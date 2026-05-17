"""
ARQ worker configuration and task definitions.
This is the main entry point for the worker process.
"""
import asyncio

from arq import cron

from app.workers import get_redis_settings
from app.workers.listener import listen_for_payments, process_single_payment
from app.workers.sweeper import sweep_funds, sweep_specific_address
from app.workers.webhook import (
    send_webhook_notification,
    retry_failed_webhooks,
    send_custom_webhook,
)
from app.services.blockchain.scanner import ScannerService
from app.core.logger import logger

# Keep references to running sniper tasks so they aren't garbage-collected
_sniper_tasks: list[asyncio.Task] = []


async def startup(ctx):  # pylint: disable=unused-argument
    """Called when worker starts — launches ChainSniper WebSocket listeners."""
    global _sniper_tasks  # pylint: disable=global-statement
    logger.info("ARQ Worker starting — launching ChainSniper listeners")
    try:
        _sniper_tasks = await ScannerService.start_listeners()
        logger.info("ChainSniper listeners started (%d chain(s))", len(_sniper_tasks))
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error("Failed to start ChainSniper listeners: %s", exc, exc_info=True)


async def shutdown(ctx):  # pylint: disable=unused-argument
    """Called when worker shuts down — cancel sniper tasks."""
    for task in _sniper_tasks:
        task.cancel()
    if _sniper_tasks:
        await asyncio.gather(*_sniper_tasks, return_exceptions=True)
    logger.info("ARQ Worker shutting down")


# Expose all task functions so ARQ can discover them
FUNCTIONS = [
    listen_for_payments,
    process_single_payment,
    sweep_funds,
    sweep_specific_address,
    send_webhook_notification,
    retry_failed_webhooks,
    send_custom_webhook,
]

CRON_JOBS = [
    # Scan for payments every second
    cron(listen_for_payments, second=set(range(60))),
    # Sweep funds every 30 seconds
    # cron(sweep_funds, second={0, 30}),
    # Retry failed webhooks every 5 minutes
    # cron(retry_failed_webhooks, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
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


__all__ = ['WorkerSettings']
