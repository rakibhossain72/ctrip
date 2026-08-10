from __future__ import annotations

import datetime
import logging
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.chains import chain_name_for_id
from app.core.config import settings
from app.db.models import Payment, PaymentStatus
from app.services.webhook import WebhookService
from scanner.constants import CONFIRMATIONS_REQUIRED

logger = logging.getLogger("scanner.lifecycle")


async def _dispatch_webhook(payment: Payment) -> None:
    if not settings.webhook_url:
        return
    payload = {
        "payment_id": str(payment.id),
        "status": payment.status.value,
        "address": payment.address,
        "amount": str(payment.amount),
        "chain": payment.chain,
        "token_contract_address": payment.token_contract_address,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    await WebhookService.send_webhook(
        settings.webhook_url, payload, settings.webhook_secret
    )


async def confirm_payments(
    db: AsyncSession,
    blockchain,
    chain_id: int,
    confirmations_required: int = CONFIRMATIONS_REQUIRED,
) -> int:
    """Promote DETECTED payments to CONFIRMED once enough blocks have passed."""
    try:
        latest_block = await blockchain.get_current_block(chain_id)
    except Exception:
        logger.exception("Error getting latest block for chain %s", chain_id)
        return 0

    result = await db.execute(
        select(Payment).where(
            and_(
                Payment.chain_id == chain_id,
                Payment.status == PaymentStatus.DETECTED,
            )
        )
    )
    confirmed = 0
    for payment in result.scalars():
        if payment.detected_in_block is None:
            continue
        depth = latest_block - payment.detected_in_block + 1
        if depth >= confirmations_required:
            payment.status = PaymentStatus.CONFIRMED
            payment.confirmations = depth
            confirmed += 1
            logger.info("Payment %s CONFIRMED on chain %s", payment.id, chain_id)
            await _dispatch_webhook(payment)

    await db.commit()
    return confirmed


async def check_expired_payments(
    db: AsyncSession, chain_id: Optional[int] = None
) -> int:
    """Mark PENDING/DETECTED payments as EXPIRED past their deadline."""
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    filters = [
        Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.DETECTED]),
        Payment.expires_at <= now,
    ]
    if chain_id is not None:
        filters.append(Payment.chain_id == chain_id)

    result = await db.execute(select(Payment).where(and_(*filters)))
    expired = list(result.scalars())
    for payment in expired:
        payment.status = PaymentStatus.EXPIRED
        logger.info(
            "Payment %s EXPIRED (chain %s)",
            payment.id,
            chain_name_for_id(payment.chain_id),
        )
        await _dispatch_webhook(payment)

    if expired:
        await db.commit()
    return len(expired)
