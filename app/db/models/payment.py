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
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


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
    token_contract_address = Column(
        String, nullable=True
    )  # ERC20 contract address; None = native token
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
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(
            tzinfo=None
        ),
        nullable=False,
    )

    api_key = relationship("ApiKey")
