"""
Pydantic schemas for analytics dashboard data.
"""

import datetime
from typing import List, Optional

from pydantic import BaseModel


class PaymentCountByStatus(BaseModel):
    """Count of payments for a single status."""

    status: str
    count: int


class PaymentVolumeSummary(BaseModel):
    """Aggregated payment counts and volumes bucketed by status."""

    total_payments: int
    total_volume_wei: str
    confirmed_volume_wei: str
    pending_count: int
    confirmed_count: int
    expired_count: int
    failed_count: int
    settled_count: int
    by_status: List[PaymentCountByStatus]


class DailyVolume(BaseModel):
    """Payment count and volume for a single day."""

    date: str
    count: int
    volume_wei: str


class ChainBreakdown(BaseModel):
    """Payment count and volume for a single blockchain."""

    chain: str
    count: int
    volume_wei: str


class WebhookStats(BaseModel):
    """Aggregated webhook delivery health metrics."""

    total_attempts: int
    successful: int
    failed: int
    pending: int
    success_rate: float
    total_retries: int


class TransactionStats(BaseModel):
    """Payment-event counts bucketed by lifecycle state."""

    total_transactions: int
    confirmed: int
    pending: int
    failed: int


class ApiKeyStats(BaseModel):
    """Aggregated API key usage metrics."""

    total_keys: int
    active_keys: int
    revoked_keys: int
    recently_used: int


class DashboardSummary(BaseModel):
    """Full dashboard payload generated at a point in time."""

    generated_at: datetime.datetime
    payments: PaymentVolumeSummary
    transactions: TransactionStats
    webhooks: WebhookStats
    api_keys: ApiKeyStats


class TransactionDetail(BaseModel):
    """One payment-event row shown in the admin detail view."""

    id: str
    tx_hash: str
    block_number: Optional[int]
    confirmations: int
    status: str

class WebhookAttemptDetail(BaseModel):
    """One webhook delivery attempt row shown in the admin detail view."""

    id: str
    event_type: str
    webhook_url: str
    status: str
    retry_count: int
    last_error: Optional[str]
    next_retry_at: Optional[str]
    created_at: str
    updated_at: str


class PaymentDetail(BaseModel):
    """Full payment detail for the admin detail view."""

    id: str
    chain: str
    api_key_name: str
    address: str
    amount_wei: str
    status: str
    confirmations: int
    detected_in_block: Optional[int]
    token_contract_address: Optional[str]
    created_at: str
    expires_at: str
    transactions: List[TransactionDetail]
    webhooks: List[WebhookAttemptDetail]
