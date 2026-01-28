"""
Main entry point for the FastAPI application.
"""
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.health import health_router
from app.api.v1.payments import router as payments_router
from app.utils.crypto import HDWalletManager
from app.blockchain.manager import get_blockchains
from app.db.session import SessionLocal
from app.db.seed import add_chain_states
from app.core.config import settings
from app.workers.listener import listen_for_payments
from app.workers.sweeper import sweep_payments


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

    add_chain_states(SessionLocal(), fastapi_app.state.blockchains)

    # Trigger background workers via Dramatiq
    listen_for_payments.send()
    sweep_payments.send()

    yield


app = FastAPI(lifespan=lifespan)
app.include_router(health_router)
app.include_router(payments_router)


@app.get("/")
def read_root():
    """
    Root endpoint for health checking and basic info.
    """
    return {"message": "Welcome to the Ctrip Payment Service"}
