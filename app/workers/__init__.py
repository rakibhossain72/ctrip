# app/workers/__init__.py
import dramatiq
from dramatiq.brokers.redis import RedisBroker
from core.config import settings

redis_broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(redis_broker)
