import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.db.async_session import get_async_db
from app.utils.helpers import now_utc, wei_to_eth_str
from app.db.models.payment import Payment, PaymentStatus
from app.db.models.transaction import Transaction
from app.db.models.webhook_attempt import WebhookAttempt
from app.db.models.api_key import ApiKey
from app.schemas.analytics import (
    PaymentCountByStatus,
    PaymentVolumeSummary,
    DailyVolume,
    ChainBreakdown,
    WebhookStats,
    TransactionStats,
    ApiKeyStats,
    DashboardSummary,
    PaymentDetail,
    TransactionDetail,
    WebhookAttemptDetail,
)

router = APIRouter(
    prefix="/admin/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin)],
)




@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_async_db)):
    """Single endpoint returning everything shown on the main dashboard."""
    payment_rows = (await db.execute(
        select(Payment.status, func.count().label("cnt"), func.sum(Payment.amount).label("vol"))
        .group_by(Payment.status)
    )).all()

    status_map: dict[str, dict] = {}
    for row in payment_rows:
        status_map[row.status.value] = {"count": row.cnt, "vol": row.vol or 0}

    def _count(s: str) -> int:
        return status_map.get(s, {}).get("count", 0)

    def _vol(s: str) -> int:
        return status_map.get(s, {}).get("vol", 0)

    confirmed_vol = _vol("paid") + _vol("settled")
    total_vol = sum(v["vol"] for v in status_map.values())
    total_payments = sum(v["count"] for v in status_map.values())

    by_status = [PaymentCountByStatus(status=s, count=d["count"]) for s, d in status_map.items()]

    payments = PaymentVolumeSummary(
        total_payments=total_payments,
        total_volume_wei=wei_to_eth_str(total_vol),
        confirmed_volume_wei=wei_to_eth_str(confirmed_vol),
        pending_count=_count("pending"),
        confirmed_count=_count("confirmed") + _count("detected"),
        expired_count=_count("expired"),
        failed_count=_count("failed"),
        settled_count=_count("settled"),
        by_status=by_status,
    )

    tx_rows = (await db.execute(
        select(Transaction.status, func.count().label("cnt")).group_by(Transaction.status)
    )).all()
    tx_map = {r.status.value: r.cnt for r in tx_rows}
    transactions = TransactionStats(
        total_transactions=sum(tx_map.values()),
        confirmed=tx_map.get("confirmed", 0),
        pending=tx_map.get("pending", 0),
        failed=tx_map.get("failed", 0),
    )

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
            func.sum(case((ApiKey.is_active == True, 1), else_=0)).label("active"),
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
    rows = (await db.execute(
        select(Payment.status, func.count().label("cnt"), func.sum(Payment.amount).label("vol"))
        .group_by(Payment.status)
    )).all()

    status_map = {r.status.value: {"count": r.cnt, "vol": r.vol or 0} for r in rows}

    def _c(s): return status_map.get(s, {}).get("count", 0)
    def _v(s): return status_map.get(s, {}).get("vol", 0)

    total_vol = sum(v["vol"] for v in status_map.values())
    total_count = sum(v["count"] for v in status_map.values())

    return PaymentVolumeSummary(
        total_payments=total_count,
        total_volume_wei=wei_to_eth_str(total_vol),
        confirmed_volume_wei=wei_to_eth_str(_v("paid") + _v("settled")),
        pending_count=_c("pending"),
        confirmed_count=_c("confirmed") + _c("detected"),
        expired_count=_c("expired"),
        failed_count=_c("failed"),
        settled_count=_c("settled"),
        by_status=[PaymentCountByStatus(status=s, count=d["count"]) for s, d in status_map.items()],
    )


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
            func.sum(Payment.amount).label("vol"),
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
        select(Payment.chain, func.count().label("cnt"), func.sum(Payment.amount).label("vol"))
        .group_by(Payment.chain)
        .order_by(func.count().desc())
    )).all()

    return [ChainBreakdown(chain=r.chain, count=r.cnt, volume_wei=wei_to_eth_str(r.vol or 0)) for r in rows]


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
            "chain": p.chain,
            "address": p.address,
            "amount_wei": wei_to_eth_str(p.amount),
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
    """Blockchain transaction counts by status."""
    rows = (await db.execute(
        select(Transaction.status, func.count().label("cnt")).group_by(Transaction.status)
    )).all()

    tx_map = {r.status.value: r.cnt for r in rows}
    return TransactionStats(
        total_transactions=sum(tx_map.values()),
        confirmed=tx_map.get("confirmed", 0),
        pending=tx_map.get("pending", 0),
        failed=tx_map.get("failed", 0),
    )


@router.get("/payments/{payment_id}", response_model=PaymentDetail)
async def get_payment_detail(payment_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """Full payment detail for admin — includes transactions and webhook attempts."""
    result = await db.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalars().first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    tx_rows = (await db.execute(
        select(Transaction).where(Transaction.payment_id == payment_id)
        .order_by(Transaction.confirmations.desc())
    )).scalars().all()

    wh_rows = (await db.execute(
        select(WebhookAttempt).where(WebhookAttempt.payment_id == str(payment_id))
        .order_by(WebhookAttempt.created_at.desc())
    )).scalars().all()

    return PaymentDetail(
        id=str(payment.id),
        chain=payment.chain,
        address=payment.address,
        amount_wei=wei_to_eth_str(payment.amount),
        status=payment.status.value,
        confirmations=payment.confirmations,
        detected_in_block=payment.detected_in_block,
        token_contract_address=payment.token_contract_address,
        created_at=payment.created_at.isoformat(),
        expires_at=payment.expires_at.isoformat(),
        transactions=[
            TransactionDetail(
                id=str(t.id),
                tx_hash=t.tx_hash,
                block_number=t.block_number,
                confirmations=t.confirmations,
                status=t.status.value,
            )
            for t in tx_rows
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
