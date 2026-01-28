"""
Base class for all database models.
"""
from sqlalchemy.orm import DeclarativeBase


# pylint: disable=too-few-public-methods
class Base(DeclarativeBase):
    """Declarative base class for SQLAlchemy models."""
