# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from core.config import settings
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

# async session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as async_sessionmaker
if SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    ASYNC_SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
elif SQLALCHEMY_DATABASE_URL.startswith("sqlite://"):
    ASYNC_SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
else:
    ASYNC_SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL
async_engine = create_async_engine(
    ASYNC_SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
)
async_session = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)