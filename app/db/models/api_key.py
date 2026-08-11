"""
Database model for API keys used to authenticate payment creation requests.

Scoped to a ``users`` row (``role='merchant'``). The raw key is returned only
once at creation; only its SHA-256 hash is stored. ``last_used_at`` is updated
lazily (not on every request) to avoid write amplification.
"""
import datetime
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._timestamps import TimestampMixin

# key_prefix covers the raw key's leading characters, used for lookup.
KEY_PREFIX_LENGTH = 12
# Lazily refresh last_used_at at most once per interval to cut write load.
LAST_USED_REFRESH_INTERVAL = datetime.timedelta(minutes=5)


class ApiKey(TimestampMixin, Base):
    """Stores hashed API keys issued to merchants/clients."""

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(
        String(KEY_PREFIX_LENGTH), nullable=False, index=True
    )
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_used_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    user = relationship("User", back_populates="api_keys")

    def should_refresh_last_used(self, now: datetime.datetime) -> bool:
        """True when the write is worth it — first use or last refresh is old."""
        if self.last_used_at is None:
            return True
        return (now - self.last_used_at) >= LAST_USED_REFRESH_INTERVAL
