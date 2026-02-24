"""
ARQ worker configuration and task definitions.
This is the main entry point for the worker process.
"""
from arq import cron
from arq.connections import RedisSettings
from app.workers import get_redis_settings
from app.workers.listener import listen_for_payments, process_single_payment
from app.workers.sweeper import sweep_funds, sweep_specific_address
from app.workers.webhook import (
    send_webhook_notification,
    retry_failed_webhooks,
    send_custom_webhook
)


async def startup(ctx):
    """Called when worker starts"""
    print("🚀 ARQ Worker started successfully")


async def shutdown(ctx):
    """Called when worker shuts down"""
    print("👋 ARQ Worker shutting down")


class WorkerSettings:
    """
    ARQ worker configuration.
    
    Defines all tasks, cron jobs, and worker settings.
    """
    # Task functions
    functions = [
        # Listener tasks
        listen_for_payments,
        process_single_payment,
        
        # Sweeper tasks
        sweep_funds,
        sweep_specific_address,
        
        # Webhook tasks
        send_webhook_notification,
        retry_failed_webhooks,
        send_custom_webhook,
    ]
    
    # Scheduled tasks (cron jobs)
    cron_jobs = [
        # Scan for payments every second
        cron(listen_for_payments, second=set(range(60))),
        
        # Sweep funds every 30 seconds
        cron(sweep_funds, second={0, 30}),
        
        # Retry failed webhooks every 5 minutes
        cron(retry_failed_webhooks, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}),
    ]
    
    # Redis connection
    redis_settings = get_redis_settings()
    
    # Worker settings
    max_jobs = 10  # Maximum concurrent jobs
    job_timeout = 300  # 5 minutes timeout per job
    keep_result = 3600  # Keep job results for 1 hour
    
    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown
    
    # Retry settings
    max_tries = 3  # Retry failed jobs up to 3 times
    retry_jobs = True  # Enable automatic retries
    
    # Health check
    health_check_interval = 60  # Check worker health every 60 seconds


# For backward compatibility and easy imports
__all__ = ['WorkerSettings']
