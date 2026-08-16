"""
Analytics API endpoints for payment and webhook statistics.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_admin
from app.db.async_session import get_async_db
from app.schemas.analytics import (
    ChainBreakdown,
    DailyVolume,
    DashboardSummary,
    PaymentDetail,
    PaymentVolumeSummary,
    TransactionStats,
    WebhookStats,
)
from app.services import admin_data

router = APIRouter(
    prefix="/admin/analytics",
    tags=["analytics"],
    dependencies=[Depends(require_admin)],
)


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(db: AsyncSession = Depends(get_async_db)):
    """Single endpoint returning everything shown on the main dashboard."""
    return await admin_data.dashboard_summary(db)


@router.get("/payments/volume", response_model=PaymentVolumeSummary)
async def payment_volume(db: AsyncSession = Depends(get_async_db)):
    """Total payment counts and volume broken down by status."""
    return await admin_data.payment_volume(db)


@router.get("/payments/daily", response_model=List[DailyVolume])
async def daily_payment_volume(
    days: int = Query(default=30, ge=1, le=365, description="Number of past days to include"),
    db: AsyncSession = Depends(get_async_db),
):
    """Payment count and volume per day for the last N days."""
    return await admin_data.daily_volume(db, days=days)


@router.get("/payments/by-chain", response_model=List[ChainBreakdown])
async def payments_by_chain(db: AsyncSession = Depends(get_async_db)):
    """Breakdown of payment count and volume per blockchain."""
    return await admin_data.payments_by_chain(db)


@router.get("/payments/recent", response_model=List[dict])
async def recent_payments(
    limit: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db: AsyncSession = Depends(get_async_db),
):
    """Most recent payments."""
    return await admin_data.recent_payments(db, limit=limit, status=status)


@router.get("/webhooks", response_model=WebhookStats)
async def webhook_stats(db: AsyncSession = Depends(get_async_db)):
    """Webhook delivery health — success rate, failures, pending retries."""
    return await admin_data.webhook_stats(db)


@router.get("/transactions", response_model=TransactionStats)
async def transaction_stats(db: AsyncSession = Depends(get_async_db)):
    """Payment-event counts bucketed by payment lifecycle state."""
    return await admin_data.transaction_stats(db)


@router.get("/payments/{payment_id}", response_model=PaymentDetail)
async def get_payment_detail(payment_id: UUID, db: AsyncSession = Depends(get_async_db)):
    """Full payment detail for admin — includes events and webhook attempts."""
    return await admin_data.payment_detail(db, payment_id)
