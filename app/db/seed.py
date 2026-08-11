"""
Database seeding utilities for initial configuration.

Seeds:
- a default admin user (login credentials)
- a default merchant user (owner for API keys / payments)
- the chains reference table, synced from chains.yaml
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blockchain.chains import load_chains
from app.core.security import hash_password
from app.db.models import Chain, User

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"
DEFAULT_MERCHANT_USERNAME = "default-merchant"


async def _ensure_user(
    db: AsyncSession, username: str, hashed_password, role: str
) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if user is None:
        user = User(
            username=username, hashed_password=hashed_password, role=role
        )
        db.add(user)
    return user


async def seed_default_data(db: AsyncSession) -> None:
    """Create the default admin/merchant users and sync chains from YAML."""
    await _ensure_user(
        db, DEFAULT_ADMIN_USERNAME, hash_password(DEFAULT_ADMIN_PASSWORD), "admin"
    )
    await _ensure_user(db, DEFAULT_MERCHANT_USERNAME, None, "merchant")

    for chain in load_chains():
        existing = await db.execute(select(Chain).where(Chain.id == chain.chain_id))
        row = existing.scalars().first()
        if row is None:
            db.add(
                Chain(
                    id=chain.chain_id,
                    name=chain.name,
                    display_name=chain.name.capitalize(),
                    is_enabled=True,
                    rpc_url=chain.primary_http_url,
                    ws_url=chain.ws_urls[0] if chain.ws_urls else None,
                    poa=chain.poa,
                )
            )
        else:
            row.name = chain.name
            row.rpc_url = chain.primary_http_url
            row.ws_url = chain.ws_urls[0] if chain.ws_urls else None
            row.poa = chain.poa

    await db.commit()


async def seed_default_admin(db: AsyncSession) -> None:
    """Backward-compatible alias used at app startup."""
    await seed_default_data(db)
