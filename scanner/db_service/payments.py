from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.chains import chain_name_for_id
from app.db.models import Payment, PaymentStatus


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_pending_native(db: AsyncSession, chain_id: int) -> dict[str, Payment]:
    """Map of lower-cased address -> Payment for pending, unexpired native
    payments on *chain_id*."""
    result = await db.execute(
        select(Payment).where(
            Payment.chain == chain_name_for_id(chain_id),
            Payment.chain_id == chain_id,
            Payment.token_contract_address.is_(None),
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
            Payment.chain == chain_name_for_id(chain_id),
            Payment.chain_id == chain_id,
            Payment.token_contract_address.is_(None).is_(False),
            Payment.token_contract_address == token_address.lower(),
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
        select(Payment.chain_id, Payment.token_contract_address).where(
            Payment.chain_id.is_not(None),
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
    """Transition a payment to DETECTED in a single round-trip."""
    result = await db.execute(
        update(Payment)
        .where(Payment.id == payment_id)
        .values(
            status=PaymentStatus.DETECTED,
            detected_in_block=block_number,
            confirmations=confirmations,
        )
    )
    return result.rowcount > 0
