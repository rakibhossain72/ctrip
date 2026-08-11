import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.blockchain.chains import chain_name_for_id
from app.db.async_session import get_async_db
from app.db.models.api_key import ApiKey
from app.db.models.chain import Chain
from app.db.models.payment import Payment, PaymentStatus
from app.db.models.payment_event import PaymentEvent
from app.db.models.webhook_attempt import WebhookAttempt
from app.schemas.analytics import (
    ApiKeyStats,
    ChainBreakdown,
    DailyVolume,
    DashboardSummary,
    PaymentCountByStatus,
    PaymentDetail,
    PaymentVolumeSummary,
    TransactionDetail,
    TransactionStats,
    WebhookAttemptDetail,
    WebhookStats,
)
from app.utils.helpers import now_utc, wei_to_eth_str

router = APIRouter(
    prefix="/admin/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin)],
)

CONFIRMED_STATES = {PaymentStatus.CONFIRMED, PaymentStatus.PAID, PaymentStatus.SETTLED}
PENDING_STATES = {PaymentStatus.PENDING, PaymentStatus.DETECTED}


async def _payment_volume_rows(db: AsyncSession) -> dict[str, dict]:
    """Status -> {count, vol} for all payments (vol in Wei)."""
    rows = (await db.execute(
        select(Payment.status, func.count().label("cnt"), func.sum(Payment.amount_raw).label("vol"))
        .group_by(Payment.status)
    )).all()
    return {r.status.value: {"count": r.cnt, "vol": r.vol or 0} for r in rows}


def _volume_summary(rows: dict[str, dict]) -> PaymentVolumeSummary:
    def _c(s: str) -> int:
        return rows.get(s, {}).get("count", 0)

    def _v(s: str) -> int:
        return rows.get(s, {}).get("vol", 0)

    total_vol = sum(v["vol"] for v in rows.values())
    total_count = sum(v["count"] for v in rows.values())

    return PaymentVolumeSummary(
        total_payments=total_count,
        total_volume_wei=wei_to_eth_str(total_vol),
        confirmed_volume_wei=wei_to_eth_str(_v("paid") + _v("settled")),
        pending_count=_c("pending"),
        confirmed_count=_c("confirmed") + _c("detected"),
        expired_count=_c("expired"),
        failed_count=_c("failed"),
        settled_count=_c("settled"),
        by_status=[PaymentCountByStatus(status=s, count=d["count"]) for s, d in rows.items()],
    )


async def _event_stats(db: AsyncSession) -> TransactionStats:
    """Payment-event stats bucketed by the payment's current lifecycle state."""
    rows = (await db.execute(
        select(Payment.status, func.count().label("cnt"))
        .select_from(PaymentEvent)
        .join(Payment, PaymentEvent.payment_id == Payment.id)
        .group_by(Payment.status)
    )).all()

    confirmed = sum(r.cnt for r in rows if r.status in CONFIRMED_STATES)
    pending = sum(r.cnt for r in rows if r.status in PENDING_STATES)
    return TransactionStats(
        total_transactions=sum(r.cnt for r in rows),
        confirmed=confirmed,
        pending=pending,
        failed=0,
    )


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_async_db)):
    """Single endpoint returning everything shown on the main dashboard."""
    status_map = await _payment_volume_rows(db)
    payments = _volume_summary(status_map)

    transactions = await _event_stats(db)

    wh_rows = (await db.execute(
        select(WebhookAttempt.status, func.count().label("cnt"), func.sum(WebhookAttempt.retry_count).label("retries"))
        .group_by(WebhookAttempt.status)
    )).all()
    wh_map = {r.status.value: {"count": r.cnt, "retries": r.retries or 0} for r in wh_rows}
    wh_total = sum(v["count"] for v in wh_map.values())
    wh_success = wh_map.get("success", {}).get("count", 0)
    webhooks = WebhookStats(
        total_attempts=wh_total,
        successful=wh_success,
        failed=wh_map.get("failed", {}).get("count", 0),
        pending=wh_map.get("pending", {}).get("count", 0),
        success_rate=round(wh_success / wh_total * 100, 2) if wh_total else 0.0,
        total_retries=sum(v["retries"] for v in wh_map.values()),
    )

    key_rows = (await db.execute(
        select(
            func.count().label("total"),
            func.sum(case((ApiKey.is_active, 1), else_=0)).label("active"),
            func.sum(case((ApiKey.last_used_at >= (now_utc() - datetime.timedelta(hours=24)), 1), else_=0)).label("recent"),
        )
    )).one()
    total_keys = key_rows.total or 0
    active_keys = key_rows.active or 0
    api_keys = ApiKeyStats(
        total_keys=total_keys,
        active_keys=active_keys,
        revoked_keys=total_keys - active_keys,
        recently_used=key_rows.recent or 0,
    )

    return DashboardSummary(
        generated_at=now_utc(),
        payments=payments,
        transactions=transactions,
        webhooks=webhooks,
        api_keys=api_keys,
    )


@router.get("/payments/volume", response_model=PaymentVolumeSummary)
async def payment_volume(db: AsyncSession = Depends(get_async_db)):
    """Total payment counts and volume broken down by status."""
    return _volume_summary(await _payment_volume_rows(db))


@router.get("/payments/daily", response_model=List[DailyVolume])
async def daily_payment_volume(
    days: int = Query(default=30, ge=1, le=365, description="Number of past days to include"),
    db: AsyncSession = Depends(get_async_db),
):
    """Payment count and volume per day for the last N days."""
    since = now_utc() - datetime.timedelta(days=days)
    rows = (await db.execute(
        select(
            func.date(Payment.created_at).label("day"),
            func.count().label("cnt"),
            func.sum(Payment.amount_raw).label("vol"),
        )
        .where(Payment.created_at >= since)
        .group_by(func.date(Payment.created_at))
        .order_by(func.date(Payment.created_at))
    )).all()

    return [DailyVolume(date=str(r.day), count=r.cnt, volume_wei=wei_to_eth_str(r.vol or 0)) for r in rows]


@router.get("/payments/by-chain", response_model=List[ChainBreakdown])
async def payments_by_chain(db: AsyncSession = Depends(get_async_db)):
    """Breakdown of payment count and volume per blockchain."""
    rows = (await db.execute(
        select(Chain.name, func.count().label("cnt"), func.sum(Payment.amount_raw).label("vol"))
        .join(Chain, Payment.chain_id == Chain.id)
        .group_by(Chain.name)
        .order_by(func.count().desc())
    )).all()

    return [ChainBreakdown(chain=r.name, count=r.cnt, volume_wei=wei_to_eth_str(r.vol or 0)) for r in rows]


@router.get("/payments/recent", response_model=List[dict])
async def recent_payments(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_async_db),
):
    """Most recent payments."""
    q = select(Payment).order_by(Payment.created_at.desc()).limit(limit)
    if status:
        try:
            enum_val = PaymentStatus(status.lower())
            q = q.where(Payment.status == enum_val)
        except ValueError:
            pass

    rows = (await db.execute(q)).scalars().all()
    return [
        {
            "id": str(p.id),
            "chain": chain_name_for_id(p.chain_id),
            "address": p.address,
            "amount_wei": wei_to_eth_str(p.amount_raw),
            "status": p.status.value,
            "confirmations": p.confirmations,
            "created_at": p.created_at.isoformat(),
            "expires_at": p.expires_at.isoformat(),
        }
        for p in rows
    ]


@router.get("/webhooks", response_model=WebhookStats)
async def webhook_stats(db: AsyncSession = Depends(get_async_db)):
    """Webhook delivery health — success rate, failures, pending retries."""
    rows = (await db.execute(
        select(WebhookAttempt.status, func.count().label("cnt"), func.sum(WebhookAttempt.retry_count).label("retries"))
        .group_by(WebhookAttempt.status)
    )).all()

    wh_map = {r.status.value: {"count": r.cnt, "retries": r.retries or 0} for r in rows}
    total = sum(v["count"] for v in wh_map.values())
    success = wh_map.get("success", {}).get("count", 0)

    return WebhookStats(
        total_attempts=total,
        successful=success,
        failed=wh_map.get("failed", {}).get("count", 0),
        pending=wh_map.get("pending", {}).get("count", 0),
        success_rate=round(success / total * 100, 2) if total else 0.0,
        total_retries=sum(v["retries"] for v in wh_map.values()),
    )


@router.get("/transactions", response_model=TransactionStats)
async def transaction_stats(db: AsyncSession = Depends(get_async_db)):
    """Payment-event counts bucketed by payment lifecycle state."""
    return await _event_stats(db)


@router.get("/payments/{payment_id}", response_model=PaymentDetail)
async def get_payment_detail(payment_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """Full payment detail for admin — includes events and webhook attempts."""
    result = await db.execute(
        select(Payment, Chain.name, ApiKey.name)
        .join(Chain, Payment.chain_id == Chain.id)
        .outerjoin(ApiKey, Payment.api_key_id == ApiKey.id)
        .where(Payment.id == payment_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment, chain_name, api_key_name = row

    event_rows = (await db.execute(
        select(PaymentEvent).where(PaymentEvent.payment_id == payment_id)
        .order_by(PaymentEvent.recorded_at.desc())
    )).scalars().all()

    wh_rows = (await db.execute(
        select(WebhookAttempt).where(WebhookAttempt.payment_id == payment_id)
        .order_by(WebhookAttempt.created_at.desc())
    )).scalars().all()

    return PaymentDetail(
        id=str(payment.id),
        chain=chain_name,
        api_key_name=api_key_name or "",
        address=payment.address,
        amount_wei=wei_to_eth_str(payment.amount_raw),
        status=payment.status.value,
        confirmations=payment.confirmations,
        detected_in_block=payment.detected_in_block,
        token_contract_address=payment.token_contract,
        created_at=payment.created_at.isoformat(),
        expires_at=payment.expires_at.isoformat(),
        transactions=[
            TransactionDetail(
                id=str(t.id),
                tx_hash=t.tx_hash,
                block_number=t.block_number,
                confirmations=t.confirmations,
                status=t.event_type.value,
            )
            for t in event_rows
        ],
        webhooks=[
            WebhookAttemptDetail(
                id=str(w.id),
                event_type=w.event_type,
                webhook_url=w.webhook_url,
                status=w.status.value,
                retry_count=w.retry_count,
                last_error=w.last_error,
                next_retry_at=w.next_retry_at.isoformat() if w.next_retry_at else None,
                created_at=w.created_at.isoformat(),
                updated_at=w.updated_at.isoformat(),
            )
            for w in wh_rows
        ],
    )
