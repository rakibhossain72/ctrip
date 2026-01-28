"""
Health check endpoints for the API.
"""
from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health", tags=["health"])
async def health_check():
    """
    Simulated health check endpoint.
    """
    return {"status": "ok"}
