"""
Database model for tracking detected blockchain transactions.
"""
import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    BigInteger,
    Enum,
    UniqueConstraint,
    ForeignKey,
)
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
    A blockchain transaction that matched a payment.

    ``dedup_key`` (``<tx_hash>:<log_index>``) is unique so re-scanned blocks
    are idempotent — the same event is never recorded twice.
    """
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    tx_hash = Column(String, nullable=False, index=True)
    log_index = Column(Integer, nullable=True)
    dedup_key = Column(String, unique=True, nullable=False, index=True)
    block_number = Column(Integer, nullable=True)
    token_contract_address = Column(String, nullable=True)
    value_raw = Column(BigInteger, nullable=True)
    confirmations = Column(Integer, default=0, nullable=False)
    status = Column(
        Enum(TransactionStatus, values_callable=lambda obj: [item.value for item in obj]),
        default=TransactionStatus.PENDING,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("tx_hash", "log_index", name="uq_transactions_tx_hash_log_index"),
    )
