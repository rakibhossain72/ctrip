"""
Main entry point for the FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from arq import create_pool
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.admin_ui import router as admin_ui_router
from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.health import health_router
from app.api.ui import router as ui_router
from app.api.v1.payments import router as payments_router
from app.blockchain.manager import get_blockchains
from app.core.config import settings
from app.db.async_session import AsyncSessionLocal
from app.db.seed import seed_default_admin
from app.wallet import WalletKeyManager
from app.workers import get_redis_settings


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
        await seed_default_admin(session)

    # Initialize Redis connection pool for background jobs
    fastapi_app.state.arq_pool = await create_pool(get_redis_settings())

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
app.include_router(admin_ui_router)
app.include_router(analytics_router)
app.include_router(ui_router)


@app.get("/")
def read_root():
    """
    Root endpoint for health checking and basic info.
    """
    return {"message": "Welcome to the Ctrip Payment Service"}
