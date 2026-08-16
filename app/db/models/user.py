"""
Unified user model — replaces ``admin_users``.

Holds both admin users (login with password, ``role='admin'``) and API-key
owners (``role='merchant'``, password optional). See Phase 7 of the
architecture redesign.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models._timestamps import TimestampMixin

ADMIN_ROLE = "admin"
MERCHANT_ROLE = "merchant"


class User(TimestampMixin, Base):
    """Unified user row for both admin and merchant accounts."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # NULL for API-key-only (merchant) users
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50), nullable=False, default=ADMIN_ROLE, server_default=ADMIN_ROLE
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    api_keys = relationship("ApiKey", back_populates="user")

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<User id={self.id} username={self.username!r} role={self.role!r}>"
