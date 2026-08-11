"""
ARQ worker configuration and task definitions.

This is the single worker process for the whole app: it runs the block
scanning orchestrator (every 10s), the payment lifecycle cron, and handles
all arq job functions (scanning, confirmations, sweeps, webhooks).
"""
from __future__ import annotations

from typing import Any

from arq import cron

from app.core.logger import listener_logger as logger
from app.db.async_session import AsyncSessionLocal
from app.db.seed import seed_default_data
from app.workers import get_redis_settings
from app.workers.listener import listen_for_payments, process_single_payment
from app.workers.sweeper import sweep_funds, sweep_specific_address
from app.workers.webhook import (
    retry_failed_webhooks,
    send_custom_webhook,
    send_webhook_notification,
)
from scanner.blockchain_service import BlockchainService
from scanner.cursor import RedisCursor
from scanner.jobs import (
    check_erc20_transfer_logs,
    check_native_transactions,
    process_block,
    process_log,
)
from scanner.orchestrator import (
    backfill_chain,
    prune_stale_cursors,
    scan_orchestrator,
)

Context = dict[str, Any]


async def startup(ctx: Context):
    """Called when worker starts — build shared services into ctx."""
    logger.info("ARQ Worker starting")
    try:
        async with AsyncSessionLocal() as db:
            await seed_default_data(db)

        blockchain_service = BlockchainService()
        ctx["blockchain_service"] = blockchain_service
        ctx["cursor"] = RedisCursor(ctx["redis"])  # arq injects the pool as ctx["redis"]
        ctx["arq_pool"] = ctx["redis"]
        ctx["db_factory"] = AsyncSessionLocal
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to initialize worker services: %s", exc, exc_info=True)
        raise


async def shutdown(ctx: Context):
    """Called when worker shuts down — release shared resources."""
    blockchain_service = ctx.get("blockchain_service")
    if blockchain_service:
        try:
            await blockchain_service.close()
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Error closing blockchain service")
    logger.info("ARQ Worker shutting down")


# All task functions so ARQ can discover them
FUNCTIONS = [
    # scanning
    check_native_transactions,
    process_block,
    check_erc20_transfer_logs,
    process_log,
    backfill_chain,
    # lifecycle
    listen_for_payments,
    process_single_payment,
    # sweeper
    sweep_funds,
    sweep_specific_address,
    # webhooks
    send_webhook_notification,
    retry_failed_webhooks,
    send_custom_webhook,
]

CRON_JOBS = [
    # Scan for new blocks every 10 seconds
    cron(scan_orchestrator, second={0, 10, 20, 30, 40, 50}),
    # Confirm / expire payments every 15 seconds
    cron(listen_for_payments, second={0, 15, 30, 45}),
    # Clean up cursors for chains with no active payments (hourly)
    cron(prune_stale_cursors, minute=0),
    # Retry failed webhooks every 5 minutes
    cron(retry_failed_webhooks, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
]


class WorkerSettings:
    """ARQ worker configuration — defines tasks, cron jobs, and worker settings."""

    functions = FUNCTIONS
    cron_jobs = CRON_JOBS
    redis_settings = get_redis_settings()

    max_jobs = 10
    job_timeout = 300
    keep_result = 3600

    on_startup = startup
    on_shutdown = shutdown

    max_tries = 3
    retry_jobs = True
    health_check_interval = 60

    def get_functions(self):
        """Return the list of registered task functions."""
        return self.functions

    def get_cron_jobs(self):
        """Return the list of scheduled cron jobs."""
        return self.cron_jobs


__all__ = ["WorkerSettings"]
