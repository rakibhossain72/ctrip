"""
id
payment_id
tx_hash
block_number
confirmations
status
"""

from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import enum
import uuid
from db.base import Base


class TransactionStatus(enum.Enum):
    """
    PENDING
    CONFIRMED
    FAILED
    """

    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)
    block_number = Column(Integer, nullable=True)
    confirmations = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.pending, nullable=False
    )
