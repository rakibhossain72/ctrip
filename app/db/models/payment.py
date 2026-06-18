"""
Database models for payments and HD wallet addresses.
"""

import datetime
import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Numeric,
    Enum,
    Integer,
    DateTime,
    ForeignKey,
    Sequence,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
from app.db.engine import DATABASE_URL

# PostgreSQL uses a named sequence for atomic, gap-free index assignment.
# SQLite does not support sequences, so we skip it for local development.
_IS_SQLITE = DATABASE_URL.startswith("sqlite")

hd_index_seq = Sequence("hdwallet_index_seq", start=0, increment=1)


class PaymentStatus(enum.Enum):
    """
    Enum for payment statuses.
    """

    PENDING = "pending"
    DETECTED = "detected"
    CONFIRMED = "confirmed"
    PAID = "paid"
    EXPIRED = "expired"
    SETTLED = "settled"
    FAILED = "failed"


# pylint: disable=too-few-public-methods
class Payment(Base):
    """
    Represents a payment request and its current state.
    """

    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token_id = Column(UUID(as_uuid=True), ForeignKey("tokens.id"), nullable=True)
    api_key_id = Column(UUID(as_uuid=True), ForeignKey("api_keys.id"), nullable=False)
    chain = Column(String, nullable=False)
    address = Column(String, nullable=False)
    amount = Column(Numeric(precision=80, scale=0), nullable=False)
    status = Column(
        Enum(PaymentStatus, values_callable=lambda obj: [item.value for item in obj]),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    confirmations = Column(Integer, default=0, nullable=False)
    detected_in_block = Column(Integer, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False
    )

    token = relationship("Token")
    api_key = relationship("ApiKey")


# pylint: disable=too-few-public-methods
class HDWalletAddress(Base):
    __tablename__ = "hdwallet_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_swapped: Mapped[bool] = mapped_column(default=False, nullable=False)
    index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)  # no sequence
    address: Mapped[str] = mapped_column(unique=True, nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False
    )