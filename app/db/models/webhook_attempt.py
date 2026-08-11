"""
Model for tracking webhook delivery attempts and retries.

Redesigned per Phase 7:
- ``payment_id`` is now a UUID FK to ``payments.id`` (C3)
- ``payload`` is structured JSON (JSONB on PostgreSQL / JSON on SQLite)
- status stored as a string column with a CHECK constraint
- composite index on ``(status, next_retry_at)`` for the retry worker (H7)
"""

from __future__ import annotations

import datetime
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._timestamps import TimestampMixin
from app.db.types import StringEnum, json_type


class WebhookAttemptStatus(enum.Enum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class WebhookAttempt(TimestampMixin, Base):
    """
    Tracks each webhook delivery attempt for a payment event.

    Failed attempts are retried by the retry_failed_webhooks cron task using
    exponential backoff up to ``MAX_RETRIES`` times.
    """

    __tablename__ = "webhook_attempts"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'success', 'failed')", name="chk_webhook_status"
        ),
        CheckConstraint(
            "retry_count >= 0 AND retry_count <= 10", name="chk_webhook_retry_count"
        ),
        Index("ix_webhooks_status_retry", "status", "next_retry_at"),
        Index("ix_webhooks_payment", "payment_id"),
        Index("ix_webhooks_created", desc("created_at")),
    )

    MAX_RETRIES = 5
    # Backoff delays in seconds: 60, 300, 900, 3600, 10800
    BACKOFF_SECONDS = [60, 300, 900, 3600, 10800]

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    webhook_url: Mapped[str] = mapped_column(String(500), nullable=False)
    payload: Mapped[dict] = mapped_column(json_type(), nullable=False)
    webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[WebhookAttemptStatus] = mapped_column(
        StringEnum(WebhookAttemptStatus),
        nullable=False,
        default=WebhookAttemptStatus.PENDING,
    )
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_retry_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
