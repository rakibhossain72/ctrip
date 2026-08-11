"""
Recording of payment status transitions into the immutable audit log
(``payment_state_changes``).
"""
from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PaymentStateChange


def record_state_changes(
    db: AsyncSession,
    *,
    payment_ids: Iterable,
    from_status: str,
    to_status: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append audit rows for a set of payments that transitioned status."""
    for payment_id in payment_ids:
        db.add(
            PaymentStateChange(
                payment_id=payment_id,
                from_status=from_status,
                to_status=to_status,
                metadata_=metadata,
            )
        )
