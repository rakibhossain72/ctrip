"""
Main entry point for the FastAPI application.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.health import health_router
from app.api.v1.payments import router as payments_router
from app.api.admin import router as admin_router
from app.utils.crypto import HDWalletManager
from app.blockchain.manager import get_blockchains
from app.db.async_session import AsyncSessionLocal
from app.db.seed import add_chain_states
from app.core.config import settings
@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """
    Handle startup and shutdown events for the FastAPI application.
    """
    # Startup
    fastapi_app.state.blockchains = get_blockchains()

    hdwallet = HDWalletManager(mnemonic_phrase=settings.mnemonic)
    fastapi_app.state.hdwallet = hdwallet

    # NOTE: Table creation now handled by Alembic migrations
    # Use: python migrate.py upgrade
    # Base.metadata.create_all(bind=engine)

    async with AsyncSessionLocal() as session:
        await add_chain_states(session, fastapi_app.state.blockchains)

    # Background workers are now handled by ARQ worker process
    # Start with: python run_worker.py
    # Workers run automatically via cron schedules

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(payments_router)
app.include_router(admin_router)


@app.get("/")
def read_root():
    """
    Root endpoint for health checking and basic info.
    """
    return {"message": "Welcome to the Ctrip Payment Service"}
