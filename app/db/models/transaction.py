"""
Database model for tracking blockchain transactions.
"""
import enum
import uuid

from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class TransactionStatus(enum.Enum):
    """
    Enum for transaction statuses.
    """
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


# pylint: disable=too-few-public-methods
class Transaction(Base):
    """
    Represents a blockchain transaction associated with a payment.
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    tx_hash = Column(String, unique=True, nullable=False)
    block_number = Column(Integer, nullable=True)
    confirmations = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(TransactionStatus), default=TransactionStatus.PENDING, nullable=False
    )
