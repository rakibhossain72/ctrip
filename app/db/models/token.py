"""
Database model for supported tokens.
"""
import uuid
from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


# pylint: disable=too-few-public-methods
class Token(Base):
    """
    Represents a supported token (Native or ERC20) on a specific blockchain.
    """
    __tablename__ = "tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain = Column(String, nullable=False, index=True)
    address = Column(String, nullable=True, index=True)  # Null for native token (e.g., ETH)
    symbol = Column(String, nullable=False)
    decimals = Column(Integer, nullable=False, default=18)
    enabled = Column(Boolean, default=True)
