"""
Database seeding utilities for initial configuration.
"""
from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import ChainState, AdminUser
from app.blockchain.base import BlockchainBase
from app.core.config import settings
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


async def add_chain_states(db: AsyncSession, chains: Dict[str, BlockchainBase]):
    """
    Ensure all configured chains have a state record in the database.
    """
    for chain_name in chains.keys():
        result = await db.execute(
            select(ChainState).where(ChainState.chain == chain_name)
        )
        existing_state = result.scalar_one_or_none()
        if not existing_state:
            chain_state = ChainState(chain=chain_name, last_scanned_block=0)
            db.add(chain_state)

    await db.commit()
