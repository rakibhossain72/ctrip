"""
Server-rendered admin console (Jinja2 templates).

Replaces the React ``admin-frontend`` app. Pages render data server-side with a
shared layout; every mutation is a plain HTML form POST using the
Post/Redirect/Get pattern with a short-lived flash cookie for one-shot toasts.

The existing JSON API under ``/admin`` (``app.api.admin``, ``app.api.analytics``)
is unchanged and still requires a Bearer token; these pages authenticate via an
HTTP-only session cookie (``get_current_admin_web``) instead.
"""
from __future__ import annotations

import base64
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    ADMIN_FLASH_COOKIE,
    ADMIN_SESSION_COOKIE,
    get_current_admin_web,
)
from app.api.templates import templates
from app.blockchain.chains import load_chains
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.async_session import get_async_db
from app.db.models.user import User
from app.services import admin_data
from app.workers.client import get_worker_client

router = APIRouter(prefix="/admin", tags=["admin-ui"])

# Mirrors the access-token lifetime in app.core.security.
SESSION_MAX_AGE = 30 * 60
# Flash cookie survives exactly one redirect.
FLASH_MAX_AGE = 60

# Chain names come from the chains.yaml configuration, not a hardcoded list.
CHAIN_NAMES = [c.name for c in load_chains()]
WEBHOOK_EVENTS = ["payment.confirmed", "payment.expired", "payment.swept"]


# ---------------------------------------------------------------------------
# Cookie / flash helpers
# ---------------------------------------------------------------------------


def _session_cookie_options() -> dict:
    return {
        "max_age": SESSION_MAX_AGE,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.env == "production",
        "path": "/",
    }


def _set_session_cookie(response, user: User) -> None:
    token = create_access_token(subject=user.username)
    response.set_cookie(ADMIN_SESSION_COOKIE, token, **_session_cookie_options())


def _encode_flash(message: str, ftype: str = "ok") -> str:
    payload = f"{ftype}|{message}".encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii")


def _decode_flash(raw: Optional[str]) -> Optional[dict]:
    if not raw:
        return None
    try:
        payload = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        ftype, _, message = payload.partition("|")
        return {"type": ftype or "ok", "message": message}
    except Exception:  # pragma: no cover - defensive  # pylint: disable=broad-exception-caught
        return None


def _set_flash(response, message: str, ftype: str = "ok") -> None:
    response.set_cookie(
        ADMIN_FLASH_COOKIE,
        _encode_flash(message, ftype),
        max_age=FLASH_MAX_AGE,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _clear_flash(response) -> None:
    response.delete_cookie(ADMIN_FLASH_COOKIE, path="/")


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------


def _render(request: Request, name: str, context: dict) -> HTMLResponse:
    """Render a template, consuming + clearing the one-shot flash cookie."""
    flash = _decode_flash(request.cookies.get(ADMIN_FLASH_COOKIE))
    ctx = {"request": request, "flash": flash}
    ctx.update(context)
    response = templates.TemplateResponse(request=request, name=name, context=ctx)
    if flash:
        _clear_flash(response)
    return response


def _safe_next(raw: Optional[str]) -> str:
    """Only redirect back inside the admin console."""
    if raw and raw.startswith("/admin") and not raw.startswith("//"):
        return raw
    return "/admin/overview"


async def _require_user(request: Request) -> Optional[User]:
    return await get_current_admin_web(request)


async def _auth_redirect() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=303)


def _redirect_with_flash(
    _request: Request, next_url: Optional[str], message: str, ftype: str = "ok"
) -> RedirectResponse:
    response = RedirectResponse(_safe_next(next_url), status_code=303)
    _set_flash(response, message, ftype)
    return response


async def _page(
    request: Request, name: str, context: dict
) -> HTMLResponse | RedirectResponse:
    """Guard a page behind the session cookie, then render it."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    return _render(request, name, {"user": user, **context})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render the admin login page."""
    if await _require_user(request):
        return RedirectResponse("/admin/overview", status_code=303)
    return _render(request, "admin/login.html", {"error": None, "flash": None})


@router.post("/login")
async def login_submit(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Process the admin login form POST."""
    form = await request.form()
    username = (form.get("username") or "").strip()
    password = form.get("password") or ""

    user = None
    if username and password:
        result = await db.execute(
            select(User).where(User.username == username, User.is_active.is_(True))
        )
        candidate = result.scalars().first()
        if (
            candidate
            and candidate.hashed_password
            and verify_password(password, candidate.hashed_password)
        ):
            user = candidate

    if user is None:
        return _render(
            request,
            "admin/login.html",
            {"error": "Invalid username or password", "flash": None},
        )

    response = RedirectResponse("/admin/overview", status_code=303)
    _set_session_cookie(response, user)
    return response


@router.post("/logout")
async def logout():
    """Clear the admin session cookie and redirect to login."""
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(ADMIN_SESSION_COOKIE, path="/")
    response.delete_cookie(ADMIN_FLASH_COOKIE, path="/")
    return response


@router.get("", response_class=HTMLResponse)
async def admin_index():
    """Redirect /admin to /admin/overview."""
    return RedirectResponse("/admin/overview", status_code=307)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


@router.get("/overview", response_class=HTMLResponse)
async def overview_page(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Render the admin dashboard overview page."""
    summary = (await admin_data.dashboard_summary(db)).model_dump(mode="json")
    payments = await admin_data.recent_payments(db, limit=8)
    webhook_rate = summary["webhooks"]["success_rate"]
    return await _page(
        request,
        "admin/dashboard.html",
        {
            "active_section": "overview",
            "summary": summary,
            "payments": payments,
            "webhook_rate": webhook_rate,
        },
    )


@router.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    status: Optional[str] = None,
    chain: Optional[str] = None,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Render the payments list page with optional filters."""
    payments = await admin_data.recent_payments(
        db, limit=100, status=status, chain=chain, search=q
    )
    return await _page(
        request,
        "admin/payments.html",
        {
            "active_section": "payments",
            "payments": payments,
            "chain_names": CHAIN_NAMES,
            "filters": {
                "status": status or "",
                "chain": chain or "",
                "q": q or "",
            },
        },
    )


@router.get("/payments/{payment_id}", response_class=HTMLResponse)
async def payment_detail_page(
    request: Request, payment_id: UUID, db: AsyncSession = Depends(get_async_db)
):
    """Render the detail page for a single payment."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    try:
        detail = await admin_data.payment_detail(db, payment_id)
        payment = detail.model_dump(mode="json")
    except Exception:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(
            request, "/admin/payments", "Payment not found", "err"
        )
    return _render(
        request,
        "admin/payment_detail.html",
        {
            "user": user,
            "active_section": "payments",
            "payment": payment,
            "chain_names": CHAIN_NAMES,
            "webhook_events": WEBHOOK_EVENTS,
        },
    )


@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    days: int = 30,
    db: AsyncSession = Depends(get_async_db),
):
    """Render the analytics dashboard page."""
    days = max(1, min(days, 365))
    volume = (await admin_data.payment_volume(db)).model_dump(mode="json")
    chains = [c.model_dump(mode="json") for c in await admin_data.payments_by_chain(db)]
    daily_rows = await admin_data.daily_volume(db, days=days)
    daily = [d.model_dump(mode="json") for d in daily_rows]

    status_total = sum(r["count"] for r in volume["by_status"]) or 1
    status_stats = [
        {
            "status": r["status"],
            "count": r["count"],
            "percent": round(r["count"] / status_total * 100),
        }
        for r in sorted(volume["by_status"], key=lambda r: r["count"], reverse=True)
    ]
    chain_total = sum(c["count"] for c in chains) or 1
    chain_stats = [
        {
            "chain": c["chain"],
            "count": c["count"],
            "volume_wei": c["volume_wei"],
            "percent": round(c["count"] / chain_total * 100),
        }
        for c in chains
    ]
    max_daily = max((d["count"] for d in daily), default=1) or 1
    daily_stats = [
        {
            "date": d["date"],
            "count": d["count"],
            "volume_wei": d["volume_wei"],
            "pct": round(d["count"] / max_daily * 100),
        }
        for d in daily
    ]
    return await _page(
        request,
        "admin/analytics.html",
        {
            "active_section": "analytics",
            "days": days,
            "status_stats": status_stats,
            "chain_stats": chain_stats,
            "daily_stats": daily_stats,
        },
    )


@router.get("/apikeys", response_class=HTMLResponse)
async def apikeys_page(request: Request, db: AsyncSession = Depends(get_async_db)):
    """Render the API keys management page."""
    keys = await admin_data.list_api_keys(db, limit=100)
    keys_data = [
        {
            "id": str(k.id),
            "name": k.name,
            "key_prefix": k.key_prefix,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]
    return await _page(
        request,
        "admin/apikeys.html",
        {"active_section": "apikeys", "keys": keys_data},
    )


@router.get("/ops", response_class=HTMLResponse)
async def ops_page(request: Request):
    """Render the operations page."""
    return await _page(
        request,
        "admin/operations.html",
        {
            "active_section": "ops",
            "chain_names": CHAIN_NAMES,
            "webhook_events": WEBHOOK_EVENTS,
        },
    )


# ---------------------------------------------------------------------------
# Actions — form POST -> redirect with flash
# ---------------------------------------------------------------------------


@router.post("/actions/scan-now")
async def action_scan_now(request: Request, client=Depends(get_worker_client)):
    """Handle the scan-now action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    try:
        await client.trigger_payment_scan()
        message = "Payment scan triggered"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, None, f"Scan failed: {e}", "err")
    return _redirect_with_flash(request, None, message)


@router.post("/actions/sweep-now")
async def action_sweep_now(request: Request, client=Depends(get_worker_client)):
    """Handle the sweep-now action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    try:
        await client.trigger_sweep()
        message = "Global sweep triggered"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, None, f"Sweep failed: {e}", "err")
    return _redirect_with_flash(request, None, message)


@router.post("/actions/sweep-address")
async def action_sweep_address(request: Request, client=Depends(get_worker_client)):
    """Handle the sweep-address action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    form = await request.form()
    address = (form.get("address") or "").strip()
    chain_name = (form.get("chain_name") or "bsc").strip()
    next_url = form.get("next") or None
    if not address:
        return _redirect_with_flash(request, next_url, "Address is required", "err")
    try:
        await client.sweep_address(address, chain_name)
        message = f"Sweep triggered for {address}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, next_url, f"Sweep failed: {e}", "err")
    return _redirect_with_flash(request, next_url, message)


@router.post("/actions/process-payment")
async def action_process_payment(request: Request, client=Depends(get_worker_client)):
    """Handle the process-payment action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    form = await request.form()
    payment_id = (form.get("payment_id") or "").strip()
    chain_name = (form.get("chain_name") or "bsc").strip()
    next_url = form.get("next") or None
    if not payment_id:
        return _redirect_with_flash(request, next_url, "Payment ID is required", "err")
    try:
        await client.process_payment(payment_id, chain_name)
        message = f"Processing payment {payment_id}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, next_url, f"Failed: {e}", "err")
    return _redirect_with_flash(request, next_url, message)


@router.post("/actions/send-webhook")
async def action_send_webhook(request: Request, client=Depends(get_worker_client)):
    """Handle the send-webhook action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    form = await request.form()
    payment_id = (form.get("payment_id") or "").strip()
    event_type = (form.get("event_type") or "payment.confirmed").strip()
    next_url = form.get("next") or None
    if not payment_id:
        return _redirect_with_flash(request, next_url, "Payment ID is required", "err")
    try:
        await client.send_webhook(payment_id, event_type)
        message = f"Webhook queued for {payment_id}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, next_url, f"Webhook failed: {e}", "err")
    return _redirect_with_flash(request, next_url, message)


@router.post("/actions/custom-webhook")
async def action_custom_webhook(request: Request, client=Depends(get_worker_client)):
    """Handle the custom-webhook action form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    form = await request.form()
    url = (form.get("url") or "").strip()
    secret = (form.get("secret") or "").strip() or None
    next_url = form.get("next") or None
    if not url:
        return _redirect_with_flash(request, next_url, "URL is required", "err")
    try:
        payload = {"test": True}
        await client.send_custom_webhook(url, payload, secret)
        message = f"Custom webhook queued to {url}"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, next_url, f"Webhook failed: {e}", "err")
    return _redirect_with_flash(request, next_url, message)


@router.post("/actions/apikeys/create")
async def action_create_api_key(
    request: Request, db: AsyncSession = Depends(get_async_db)
):
    """Handle the API key creation form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    form = await request.form()
    name = (form.get("name") or "").strip()
    next_url = form.get("next") or None
    if not name:
        return _redirect_with_flash(request, next_url, "Key name is required", "err")
    _, raw_key = await admin_data.create_api_key(db, user, name)
    return _redirect_with_flash(request, next_url, raw_key, "raw_key")


@router.post("/actions/apikeys/{key_id}/revoke")
async def action_revoke_api_key(
    key_id: UUID, request: Request, db: AsyncSession = Depends(get_async_db)
):
    """Handle the API key revocation form POST."""
    user = await _require_user(request)
    if user is None:
        return await _auth_redirect()
    next_url = (await request.form()).get("next") or None
    try:
        await admin_data.revoke_api_key(db, key_id)
        message = "API key revoked"
    except Exception as e:  # pylint: disable=broad-exception-caught
        return _redirect_with_flash(request, next_url, str(e), "err")
    return _redirect_with_flash(request, next_url, message)
