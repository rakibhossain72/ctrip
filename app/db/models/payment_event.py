"""
Append-only record of every on-chain transfer matched to a payment.

Replaces the old ``transactions`` table. ``(tx_hash, log_index)`` is unique so
re-scanned blocks are idempotent: the scanner inserts with
``ON CONFLICT DO NOTHING`` (see C1 in the redesign).
"""

from __future__ import annotations

import datetime
import enum
import uuid

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._timestamps import utcnow
from app.db.types import StringEnum

# Native transfers have no log index, but a NULL log_index would be treated as
# distinct by UNIQUE constraints (PostgreSQL and SQLite alike), silently
# breaking idempotency. A sentinel that can never collide with a real log index
# keeps ``UNIQUE(tx_hash, log_index)`` meaningful for native events too.
NATIVE_LOG_INDEX = -1


class PaymentEventType(enum.Enum):
    """Kind of on-chain event matched to a payment."""

    NATIVE = "native"
    ERC20 = "erc20"


class PaymentEvent(Base):
    """Append-only record of an on-chain transfer matched to a payment."""
    __table_args__ = (
        UniqueConstraint("tx_hash", "log_index", name="ux_payment_events_tx_log"),
        CheckConstraint(
            "event_type IN ('native', 'erc20')", name="chk_event_type"
        ),
        CheckConstraint("value_raw > 0", name="chk_event_value_positive"),
        Index("ix_payment_events_payment_recorded", "payment_id", "recorded_at"),
        Index("ix_payment_events_chain_block", "chain_id", "block_number"),
        Index("ix_payment_events_to_address", "to_address", "recorded_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    chain_id: Mapped[int] = mapped_column(
        ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False
    )
    event_type: Mapped[PaymentEventType] = mapped_column(
        StringEnum(PaymentEventType), nullable=False
    )
    tx_hash: Mapped[str] = mapped_column(String(66), nullable=False)
    # NULL for native transfers; see NATIVE_LOG_INDEX above.
    log_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_contract: Mapped[str | None] = mapped_column(String(42), nullable=True)
    value_raw: Mapped[int] = mapped_column(BigInteger, nullable=False)
    from_address: Mapped[str] = mapped_column(String(42), nullable=False)
    to_address: Mapped[str] = mapped_column(String(42), nullable=False)
    block_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
