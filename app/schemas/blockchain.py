import time
from dataclasses import dataclass, field
from enum import Enum

from app.core.logger import logger


class ProviderType(Enum):
    HTTP = "http"
    WSS = "wss"


#  RPCEndpoint  –  one node in the pool
@dataclass
class RPCEndpoint:
    url: str
    provider_type: ProviderType
    weight: int = 1  # Higher weight = picked more often
    max_failures: int = 3
    cooldown_seconds: float = 30.0

    # runtime state
    _failures: int = field(default=0, init=False, repr=False)
    _healthy: bool = field(default=True, init=False, repr=False)
    _last_failure_time: float = field(default=0.0, init=False, repr=False)
    _total_requests: int = field(default=0, init=False, repr=False)
    _latency_ema_ms: float = field(default=0.0, init=False, repr=False)

    @property
    def is_healthy(self) -> bool:
        if self._healthy:
            return True
        if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
            self._healthy = True
            self._failures = 0
            logger.info(f"[RPC] Auto-recovered: {self.url}")
        return self._healthy

    def record_success(self, latency_ms: float = 0.0):
        self._failures = 0
        self._healthy = True
        self._total_requests += 1
        # exponential moving average
        self._latency_ema_ms = self._latency_ema_ms * 0.8 + latency_ms * 0.2

    def record_failure(self):
        self._failures += 1
        self._last_failure_time = time.monotonic()
        self._total_requests += 1
        if self._failures >= self.max_failures:
            self._healthy = False
            logger.warning(
                f"[RPC] Marked unhealthy ({self._failures} failures): {self.url}"
            )

    def stats(self) -> dict:
        return {
            "url": self.url,
            "type": self.provider_type.value,
            "healthy": self._healthy,
            "failures": self._failures,
            "total_requests": self._total_requests,
            "latency_ms": round(self._latency_ema_ms, 2),
        }
