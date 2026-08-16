"""
Payment lifecycle helpers: confirmation and expiration checks.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from scanner.constants import CONFIRMATIONS_REQUIRED
from scanner.db_service.payments import (
    bulk_confirm_payments,
    bulk_expire_payments,
)

logger = logging.getLogger("scanner.lifecycle")


async def _enqueue_webhook(ctx: dict, payment_id, event_type: str) -> None:
    """Enqueue a webhook delivery job so attempts are recorded and retried."""
    if not settings.webhook_url:
        return
    arq_pool = ctx.get("arq_pool")
    if arq_pool is None:
        return
    await arq_pool.enqueue_job("send_webhook_notification", payment_id, event_type)


async def confirm_payments(
    ctx: dict,
    db: AsyncSession,
    chain_id: int,
    confirmations_required: int = CONFIRMATIONS_REQUIRED,
) -> int:
    """Promote DETECTED payments to CONFIRMED once enough blocks have passed."""
    blockchain = ctx["blockchain_service"]
    try:
        latest_block = await blockchain.get_current_block(chain_id)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Error getting latest block for chain %s", chain_id)
        return 0

    confirmed = await bulk_confirm_payments(
        db, chain_id, latest_block, confirmations_required
    )
    for payment in confirmed:
        logger.info("Payment %s CONFIRMED on chain %s", payment.id, chain_id)
        await _enqueue_webhook(ctx, payment.id, "payment.confirmed")

    await db.commit()
    return len(confirmed)


async def check_expired_payments(
    ctx: dict, db: AsyncSession, chain_id: Optional[int] = None
) -> int:
    """Mark PENDING/DETECTED payments as EXPIRED past their deadline."""
    expired = await bulk_expire_payments(db, chain_id)
    for payment in expired:
        logger.info("Payment %s EXPIRED (chain %s)", payment.id, payment.chain_id)
        await _enqueue_webhook(ctx, payment.id, "payment.expired")

    if expired:
        await db.commit()
    return len(expired)
