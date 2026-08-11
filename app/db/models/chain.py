"""
Reference table for configured blockchains.

Seeded from ``chains.yaml`` on startup so the database owns chain metadata that
the scanner and API filter on. ``id`` is the EVM chain id (from
``chains.yaml``'s ``chain_id``), which keeps ``payments.chain_id`` semantics
identical to the pre-redesign schema.
"""

from __future__ import annotations

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models._timestamps import utcnow


class Chain(Base):
    __tablename__ = "chains"

    id: Mapped[int] = mapped_column(primary_key=True)  # EVM chain id
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rpc_url: Mapped[str] = mapped_column(String(500), nullable=False)
    ws_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    poa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[object] = mapped_column(DateTime, nullable=False, default=utcnow)
    updated_at: Mapped[object] = mapped_column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return f"<Chain id={self.id} name={self.name!r}>"
