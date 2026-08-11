"""
Immutable audit log of payment status transitions.

Append-only; written alongside every status change (detected, confirmed,
expired, settled). The ``metadata_`` attribute maps to the ``metadata`` JSONB
column — the name avoids SQLAlchemy's reserved declarative attribute.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._timestamps import utcnow
from app.db.types import json_type


class PaymentStateChange(Base):
    __tablename__ = "payment_state_changes"
    __table_args__ = (
        Index("ix_state_changes_payment_time", "payment_id", "changed_at"),
        Index("ix_state_changes_time", "changed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str] = mapped_column(String(20), nullable=False)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, default=utcnow
    )
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", json_type(), nullable=True
    )
