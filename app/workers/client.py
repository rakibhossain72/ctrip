"""
ARQ client for enqueuing tasks from FastAPI endpoints.
"""
from typing import Optional, Dict, Any
from arq import create_pool
from arq.connections import ArqRedis
from app.workers import get_redis_settings
from app.core.logger import logger


class WorkerClient:
    """
    Client for enqueuing background tasks.
    Use this in your FastAPI endpoints to trigger worker tasks.
    """
    
    def __init__(self):
        self._pool: Optional[ArqRedis] = None
    
    async def get_pool(self) -> ArqRedis:
        """Get or create Redis connection pool"""
        if self._pool is None:
            self._pool = await create_pool(get_redis_settings())
        return self._pool
    
    async def close(self):
        """Close the connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
    
    # Listener tasks
    async def trigger_payment_scan(self) -> str:
        """Trigger immediate payment scan"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('listen_for_payments')
        logger.info(f"Enqueued payment scan job: {job.job_id}")
        return job.job_id
    
    async def process_payment(self, payment_id: int, chain_name: str) -> str:
        """Process a specific payment"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('process_single_payment', payment_id, chain_name)
        logger.info(f"Enqueued payment processing job: {job.job_id}")
        return job.job_id
    
    # Sweeper tasks
    async def trigger_sweep(self) -> str:
        """Trigger immediate fund sweep"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('sweep_funds')
        logger.info(f"Enqueued sweep job: {job.job_id}")
        return job.job_id
    
    async def sweep_address(self, address: str, chain_name: str) -> str:
        """Sweep a specific address"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('sweep_specific_address', address, chain_name)
        logger.info(f"Enqueued address sweep job: {job.job_id}")
        return job.job_id
    
    # Webhook tasks
    async def send_webhook(self, payment_id: int, event_type: str) -> str:
        """Send webhook notification"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('send_webhook_notification', payment_id, event_type)
        logger.info(f"Enqueued webhook job: {job.job_id}")
        return job.job_id
    
    async def send_custom_webhook(
        self, 
        url: str, 
        payload: Dict[str, Any], 
        secret: Optional[str] = None
    ) -> str:
        """Send custom webhook"""
        pool = await self.get_pool()
        job = await pool.enqueue_job('send_custom_webhook', url, payload, secret)
        logger.info(f"Enqueued custom webhook job: {job.job_id}")
        return job.job_id
    
    # Job status
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a job"""
        pool = await self.get_pool()
        job = await pool.get_job(job_id)
        if job:
            return {
                'job_id': job.job_id,
                'status': await job.status(),
                'result': await job.result(),
            }
        return None


# Global client instance
worker_client = WorkerClient()


# Dependency for FastAPI
async def get_worker_client() -> WorkerClient:
    """FastAPI dependency to get worker client"""
    return worker_client
