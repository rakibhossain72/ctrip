# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings   # ← your settings / env variables
ENVIRONMENT = settings.env
if ENVIRONMENT == "production":
    SQLALCHEMY_DATABASE_URL = settings.database_url_prod
else:
    SQLALCHEMY_DATABASE_URL = settings.database_url_dev

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,           # very useful in production
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)

# This is the factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=Session,               # optional but explicit
)

# This is what you use in Depends()
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()