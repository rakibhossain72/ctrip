"""
ARQ worker initialization and configuration.
"""
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings
from urllib.parse import urlparse

def get_redis_settings() -> RedisSettings:
    """Parse Redis URL and return ARQ RedisSettings"""
    parsed = urlparse(settings.redis_url)
    return RedisSettings(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip('/')) if parsed.path else 0,
    )

# Export for easy imports
__all__ = ['get_redis_settings', 'create_pool']
