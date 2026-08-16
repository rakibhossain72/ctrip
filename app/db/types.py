"""
Shared SQLAlchemy column types used across the models.

- ``StringEnum`` stores an enum's ``.value`` in a plain VARCHAR column (the
  redesigned schema uses string status columns with CHECK constraints) while
  still presenting the enum object to application code.
- ``json_type()`` returns JSONB on PostgreSQL and plain JSON elsewhere so the
  models remain SQLite-compatible (the dev database).
"""

from __future__ import annotations

from enum import Enum
from typing import Type

from sqlalchemy import JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeDecorator

from app.db.engine import ASYNC_DATABASE_URL


class StringEnum(TypeDecorator):  # pylint: disable=too-many-ancestors
    """Persist ``enum.value`` in a VARCHAR column, round-tripping back to the
    enum instance on read. Backed by a native string type so CHECK constraints
    and plain string filters behave exactly like the schema documents them."""

    impl = String
    cache_ok = True

    def __init__(self, enum_class: Type[Enum], length: int = 20) -> None:
        super().__init__(length=length)
        self.enum_class = enum_class

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.enum_class(value)


def json_type():
    """JSONB on PostgreSQL, plain JSON everywhere else (SQLite-compatible)."""
    if "postgresql" in ASYNC_DATABASE_URL:
        return JSONB()
    return JSON()
