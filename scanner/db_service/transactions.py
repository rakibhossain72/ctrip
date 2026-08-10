from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Transaction


def make_dedup_key(tx_hash: str, log_index: Optional[int] = None) -> str:
    return f"{tx_hash}:{log_index if log_index is not None else 0}"


async def transaction_exists(db: AsyncSession, dedup_key: str) -> bool:
    result = await db.execute(
        select(Transaction.id).where(Transaction.dedup_key == dedup_key)
    )
    return result.scalar_one_or_none() is not None


async def record_transaction(
    db: AsyncSession,
    *,
    payment_id,
    tx_hash: str,
    block_number: int,
    value_raw: int,
    token_contract_address: Optional[str] = None,
    log_index: Optional[int] = None,
) -> bool:
    """
    Persist a matched transfer idempotently.

    Returns True if a new row was written, False if this event was already
    recorded (e.g. the block range was re-scanned or a job retried).
    """
    dedup_key = make_dedup_key(tx_hash, log_index)
    if await transaction_exists(db, dedup_key):
        return False

    db.add(
        Transaction(
            payment_id=payment_id,
            tx_hash=tx_hash,
            log_index=log_index,
            dedup_key=dedup_key,
            block_number=block_number,
            token_contract_address=token_contract_address,
            value_raw=value_raw,
            confirmations=0,
        )
    )
    return True
