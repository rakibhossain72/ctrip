"""
Main entry point for the FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.api.health import health_router
from app.api.v1.payments import router as payments_router
from app.api.admin import router as admin_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.ui import router as ui_router

from app.wallet import WalletKeyManager
from app.blockchain.manager import get_blockchains
from app.db.async_session import AsyncSessionLocal
from app.db.seed import add_chain_states, seed_default_admin
from app.core.config import settings
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """
    Handle startup and shutdown events for the FastAPI application.
    """
    # Startup
    fastapi_app.state.blockchains = get_blockchains()

    wallet_manager = WalletKeyManager(
        server_secret_a=settings.wallet_secret_a,
        server_secret_b=settings.wallet_secret_b,
    )
    fastapi_app.state.wallet_manager = wallet_manager

    # NOTE: Table creation now handled by Alembic migrations
    # Use: python migrate.py upgrade
    # Base.metadata.create_all(bind=engine)

    async with AsyncSessionLocal() as session:
        await add_chain_states(session, fastapi_app.state.blockchains)
        await seed_default_admin(session)

    # Background workers are now handled by ARQ worker process
    # Start with: python run_worker.py
    # Workers run automatically via cron schedules

    yield


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:3000",  # React
    "http://localhost:5173",  # Vite
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(payments_router)
app.include_router(admin_router)
app.include_router(analytics_router)
app.include_router(ui_router)


@app.get("/")
def read_root():
    """
    Root endpoint for health checking and basic info.
    """
    return {"message": "Welcome to the Ctrip Payment Service"}
