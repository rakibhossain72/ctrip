"""
Database model for payment requests and their current state.

Redesigned per Phase 7 of the architecture document:
- ``amount`` -> ``amount_raw`` (BigInteger, Wei / token base units)
- ``chain`` removed (derivable from ``chain_id`` via the ``chains`` table)
- ``token_contract_address`` -> ``token_contract``
- ``chain_id`` now NOT NULL with a FK to ``chains.id``
- ``user_id`` added (owner), plus ``detected_at`` / ``settled_at`` / ``updated_at``
- status stored as a string column (with CHECK constraint) instead of a native enum
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
    Uuid,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._timestamps import TimestampMixin
from app.db.types import StringEnum


class PaymentStatus(enum.Enum):
    """Enum for payment statuses — stored as string values in the DB."""

    PENDING = "pending"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    PAID = "paid"
    EXPIRED = "expired"
    SETTLED = "settled"
    FAILED = "failed"


class Payment(TimestampMixin, Base):
    """A payment request and its lifecycle state."""

    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'detected', 'confirmed', 'paid', "
            "'expired', 'settled', 'failed')",
            name="chk_payment_status",
        ),
        CheckConstraint("amount_raw > 0", name="chk_payment_amount_positive"),
        CheckConstraint("length(address) = 42", name="chk_payment_address_length"),
        Index("ix_payments_chain_status_expires", "chain_id", "status", "expires_at"),
        Index("ix_payments_user_created", "user_id", desc("created_at")),
        Index("ix_payments_api_key_created", "api_key_id", desc("created_at")),
        Index("ix_payments_status_created", "status", "created_at"),
        Index("ix_payments_address", "address"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    api_key_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("api_keys.id", ondelete="RESTRICT"), nullable=False
    )
    chain_id: Mapped[int] = mapped_column(
        ForeignKey("chains.id", ondelete="RESTRICT"), nullable=False
    )
    address: Mapped[str] = mapped_column(String(42), nullable=False)
    amount_raw: Mapped[int] = mapped_column(BigInteger, nullable=False)
    token_contract: Mapped[str | None] = mapped_column(String(42), nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        StringEnum(PaymentStatus), nullable=False, default=PaymentStatus.PENDING
    )
    confirmations: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detected_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    detected_in_block: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    settled_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    api_key = relationship("ApiKey")
