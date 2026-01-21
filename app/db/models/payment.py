"""
id (uuid)
chain
address
amount
status (pending/paid/expired)
confirmations
expires_at
created_at
"""

from sqlalchemy import Column, String, Numeric, Enum, Integer, DateTime, BigInteger
from sqlalchemy.dialects.postgresql import UUID
import enum
import datetime
import uuid
from db.base import Base


class PaymentStatus(enum.Enum):
    """
    PENDING
    PAID
    CONFIRMED
    EXPIRED
    SETTLED
    FAILED
    """

    pending = "pending"
    paid = "paid"
    expired = "expired"
    settled = "settled"
    failed = "failed"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain = Column(String, nullable=False)
    address = Column(String, nullable=False)
    amount = Column(Numeric(precision=80, scale=0), nullable=False)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    confirmations = Column(Integer, default=0, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False
    )
