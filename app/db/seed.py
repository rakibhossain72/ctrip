"""
Database seeding utilities for initial configuration.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AdminUser
from app.core.security import hash_password

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"


async def seed_default_admin(db: AsyncSession):
    """Create the default admin user if none exists."""
    result = await db.execute(select(AdminUser))
    if result.scalars().first():
        return

    db.add(AdminUser(
        username=DEFAULT_ADMIN_USERNAME,
        hashed_password=hash_password(DEFAULT_ADMIN_PASSWORD),
    ))
    await db.commit()
