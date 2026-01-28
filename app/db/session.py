"""
Synchronous database session management.
"""
from typing import Generator
from sqlalchemy.orm import sessionmaker, Session
from app.db.engine import engine

# pylint: disable=invalid-name
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting synchronous database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
