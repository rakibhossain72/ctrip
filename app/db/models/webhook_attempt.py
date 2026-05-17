"""
Model for tracking webhook delivery attempts and retries.
"""
import datetime
import enum
import uuid

from sqlalchemy import Column, String, Integer, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class WebhookAttemptStatus(enum.Enum):
    """Status of a webhook delivery attempt."""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


# pylint: disable=too-few-public-methods
class WebhookAttempt(Base):
    """
    Tracks each webhook delivery attempt for a payment event.
    Failed attempts are retried by the retry_failed_webhooks cron task
    using exponential backoff up to MAX_RETRIES times.
    """
    __tablename__ = "webhook_attempts"

    MAX_RETRIES = 5
    # Backoff delays in seconds: 60, 300, 900, 3600, 10800
    BACKOFF_SECONDS = [60, 300, 900, 3600, 10800]

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    webhook_url = Column(String, nullable=False)
    payload = Column(Text, nullable=False)          # JSON-serialised payload
    webhook_secret = Column(String, nullable=True)
    status = Column(
        Enum(WebhookAttemptStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=WebhookAttemptStatus.PENDING,
        nullable=False,
        index=True,
    )
    retry_count = Column(Integer, default=0, nullable=False)
    last_error = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(
        DateTime,
        default=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=datetime.datetime.now(datetime.timezone.utc),
        onupdate=datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
