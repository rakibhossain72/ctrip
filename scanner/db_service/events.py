"""
Persist matched on-chain transfer events into ``payment_events`` idempotently.

Fixes the C1 race condition from the redesign: the insert uses
``ON CONFLICT (tx_hash, log_index) DO NOTHING`` instead of the old
SELECT-then-INSERT pattern, so concurrent scanners can never collide on the
unique constraint.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentEvent, PaymentEventType
from app.db.models.payment_event import NATIVE_LOG_INDEX


def _dialect_insert(db: AsyncSession):
    """Return a dialect-specific Insert supporting ON CONFLICT / RETURNING."""
    dialect = db.get_bind().dialect.name
    if dialect == "sqlite":
        return sqlite.insert
    return postgresql.insert


async def record_event(
    db: AsyncSession,
    *,
    payment_id,
    chain_id: int,
    event_type: PaymentEventType,
    tx_hash: str,
    value_raw: int,
    block_number: int,
    to_address: str,
    from_address: str,
    token_contract: Optional[str] = None,
    log_index: Optional[int] = None,
) -> bool:
    """
    Record a matched transfer atomically.

    Returns True if a new row was written, False if this event was already
    recorded (e.g. the block range was re-scanned or a job retried).
    """
    if event_type == PaymentEventType.NATIVE:
        # See NATIVE_LOG_INDEX: a sentinel keeps UNIQUE(tx_hash, log_index)
        # meaningful for events that have no ERC-20 log index.
        log_index = NATIVE_LOG_INDEX

    result = await db.execute(
        _dialect_insert(db)(PaymentEvent)
        .values(
            payment_id=payment_id,
            chain_id=chain_id,
            event_type=event_type,
            tx_hash=tx_hash,
            log_index=log_index,
            token_contract=token_contract,
            value_raw=value_raw,
            from_address=from_address,
            to_address=to_address,
            block_number=block_number,
            confirmations=0,
        )
        .on_conflict_do_nothing(index_elements=["tx_hash", "log_index"])
        .returning(PaymentEvent.id)
    )
    return result.first() is not None
