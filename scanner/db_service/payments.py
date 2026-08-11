"""
Payment queries and status transitions used by the block scanner.

Aligns with Phase 12 of the redesign: the scanner loads only *pending*
payments it needs to watch, and state changes are done as guarded bulk
UPDATEs with ``RETURNING`` instead of read-modify-write loops (H8/H9, C2).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Payment, PaymentStatus
from scanner.db_service.state_changes import record_state_changes


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_pending_native(db: AsyncSession, chain_id: int) -> dict[str, Payment]:
    """Map of lower-cased address -> Payment for pending, unexpired native
    payments on *chain_id*."""
    result = await db.execute(
        select(Payment).where(
            Payment.chain_id == chain_id,
            Payment.token_contract.is_(None),
            Payment.status == PaymentStatus.PENDING,
            Payment.expires_at > _now(),
        )
    )
    return {p.address.lower(): p for p in result.scalars().all()}


async def get_pending_erc20(
    db: AsyncSession, chain_id: int, token_address: str
) -> dict[str, Payment]:
    """Map of lower-cased address -> Payment for pending, unexpired ERC-20
    payments for *token_address* on *chain_id*."""
    result = await db.execute(
        select(Payment).where(
            Payment.chain_id == chain_id,
            Payment.token_contract == token_address.lower(),
            Payment.status == PaymentStatus.PENDING,
            Payment.expires_at > _now(),
        )
    )
    return {p.address.lower(): p for p in result.scalars().all()}


async def active_scan_targets(db: AsyncSession) -> dict[int, dict]:
    """
    Scan spec for every chain that currently has pending, unexpired payments.

    Returns {chain_id: {"native": bool, "tokens": set[str]}}. Tokens are
    lower-cased contract addresses; native is True when at least one pending
    payment has no token contract.
    """
    result = await db.execute(
        select(Payment.chain_id, Payment.token_contract).where(
            Payment.status == PaymentStatus.PENDING,
            Payment.expires_at > _now(),
        )
    )
    targets: dict[int, dict] = {}
    for chain_id, token in result.all():
        spec = targets.setdefault(chain_id, {"native": False, "tokens": set()})
        if token is None:
            spec["native"] = True
        else:
            spec["tokens"].add(token.lower())
    return targets


async def mark_detected(
    db: AsyncSession, payment_id, block_number: int, confirmations: int = 1
) -> bool:
    """
    Transition a PENDING payment to DETECTED in a single guarded UPDATE.

    The ``status = 'pending'`` guard (C2) prevents a payment that another
    worker already confirmed/expired from being reverted back to DETECTED.
    """
    now = _now()
    result = await db.execute(
        update(Payment)
        .where(
            Payment.id == payment_id,
            Payment.status == PaymentStatus.PENDING,
        )
        .values(
            status=PaymentStatus.DETECTED,
            detected_in_block=block_number,
            detected_at=now,
            confirmations=confirmations,
            updated_at=now,
        )
        .returning(Payment.id)
    )
    row = result.first()
    if row is not None:
        record_state_changes(
            db,
            payment_ids=[row[0]],
            from_status="pending",
            to_status="detected",
            metadata={
                "block_number": block_number,
                "confirmations": confirmations,
            },
        )
        return True
    return False


async def bulk_confirm_payments(
    db: AsyncSession,
    chain_id: int,
    latest_block: int,
    confirmations_required: int,
) -> list[Payment]:
    """
    Promote DETECTED payments past the confirmation depth to CONFIRMED in one
    bulk UPDATE ... RETURNING (H9). Returns the updated payments.
    """
    now = _now()
    depth = latest_block - Payment.detected_in_block + 1
    result = await db.execute(
        update(Payment)
        .where(
            Payment.chain_id == chain_id,
            Payment.status == PaymentStatus.DETECTED,
            Payment.detected_in_block.is_not(None),
            depth >= confirmations_required,
        )
        .values(
            status=PaymentStatus.CONFIRMED,
            confirmations=depth,
            updated_at=now,
        )
        .returning(Payment)
    )
    confirmed = list(result.scalars())
    if confirmed:
        record_state_changes(
            db,
            payment_ids=[p.id for p in confirmed],
            from_status="detected",
            to_status="confirmed",
            metadata={
                "block_number": latest_block,
                "confirmations_required": confirmations_required,
            },
        )
    return confirmed


async def bulk_expire_payments(
    db: AsyncSession, chain_id: Optional[int] = None
) -> list[Payment]:
    """
    Mark PENDING/DETECTED payments past their deadline as EXPIRED in one bulk
    UPDATE ... RETURNING (H9). Returns the updated payments.
    """
    now = _now()
    filters = [
        Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.DETECTED]),
        Payment.expires_at <= now,
    ]
    if chain_id is not None:
        filters.append(Payment.chain_id == chain_id)

    # Capture prior statuses so the audit log is accurate.
    prior = {
        row[0]: row[1].value
        for row in (await db.execute(select(Payment.id, Payment.status).where(*filters))).all()
    }

    result = await db.execute(
        update(Payment)
        .where(*filters)
        .values(status=PaymentStatus.EXPIRED, updated_at=now)
        .returning(Payment)
    )
    expired = list(result.scalars())
    for payment in expired:
        record_state_changes(
            db,
            payment_ids=[payment.id],
            from_status=prior.get(payment.id, "pending"),
            to_status="expired",
            metadata={"expired_at": now.isoformat()},
        )
    return expired
