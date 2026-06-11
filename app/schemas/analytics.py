import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class PaymentCountByStatus(BaseModel):
    status: str
    count: int


class PaymentVolumeSummary(BaseModel):
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
    date: str
    count: int
    volume_wei: str


class ChainBreakdown(BaseModel):
    chain: str
    count: int
    volume_wei: str


class WebhookStats(BaseModel):
    total_attempts: int
    successful: int
    failed: int
    pending: int
    success_rate: float
    total_retries: int


class TransactionStats(BaseModel):
    total_transactions: int
    confirmed: int
    pending: int
    failed: int


class ApiKeyStats(BaseModel):
    total_keys: int
    active_keys: int
    revoked_keys: int
    recently_used: int


class DashboardSummary(BaseModel):
    generated_at: datetime.datetime
    payments: PaymentVolumeSummary
    transactions: TransactionStats
    webhooks: WebhookStats
    api_keys: ApiKeyStats


class TransactionDetail(BaseModel):
    id: str
    tx_hash: str
    block_number: Optional[int]
    confirmations: int
    status: str


class WebhookAttemptDetail(BaseModel):
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
    id: str
    chain: str
    address: str
    amount_wei: str
    status: str
    confirmations: int
    detected_in_block: Optional[int]
    token_id: Optional[str]
    created_at: str
    expires_at: str
    transactions: List[TransactionDetail]
    webhooks: List[WebhookAttemptDetail]
