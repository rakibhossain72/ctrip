"""
Shared timestamp helpers for the database models.

Every table tracks ``created_at`` and (except append-only history tables)
``updated_at`` to satisfy the audit-trail requirement of the redesign.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime.datetime:
    """Timezone-naive UTC now — matches the existing app-wide convention."""
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    """Adds ``created_at`` / ``updated_at`` columns to a model."""

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow, onupdate=utcnow
    )
