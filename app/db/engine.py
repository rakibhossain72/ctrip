from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

def get_database_url() -> str:
    return (
        settings.database_url_prod
        if settings.env == "production"
        else settings.database_url_dev
    )

def make_async_url(url: str) -> str:
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    return url

DATABASE_URL = get_database_url()
ASYNC_DATABASE_URL = make_async_url(DATABASE_URL)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
)

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=True,
)
