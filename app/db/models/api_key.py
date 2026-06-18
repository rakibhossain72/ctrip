"""
Database model for API keys used to authenticate payment creation requests.
"""
import datetime
import uuid

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


# pylint: disable=too-few-public-methods
class ApiKey(Base):
    """
    Stores hashed API keys issued to merchants/clients.
    The raw key is only returned once at creation time.
    """
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)                    # Human-readable label
    key_prefix = Column(String(8), nullable=False, index=True)  # First 8 chars for lookup
    hashed_key = Column(String, nullable=False, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
        nullable=False,
    )
    last_used_at = Column(DateTime, nullable=True)
