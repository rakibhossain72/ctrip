"""
Schemas for blockchain RPC endpoint configuration and health tracking.
"""

import time
from dataclasses import dataclass, field
from enum import Enum

from app.core.logger import logger


class ProviderType(Enum):
    """Transport protocol for an RPC endpoint."""

    HTTP = "http"
    WSS = "wss"


#  RPCEndpoint  –  one node in the pool
@dataclass
class RPCEndpoint:
    """One node in the RPC endpoint pool with health and latency tracking."""
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
        """True when the endpoint is healthy or past its cooldown window."""
        if self._healthy:
            return True
        if time.monotonic() - self._last_failure_time >= self.cooldown_seconds:
            self._healthy = True
            self._failures = 0
            logger.info("[RPC] Auto-recovered: %s", self.url)
        return self._healthy

    def record_success(self, latency_ms: float = 0.0):
        """Mark a successful request and update the latency EMA."""

        self._failures = 0
        self._healthy = True
        self._total_requests += 1
        # exponential moving average
        self._latency_ema_ms = self._latency_ema_ms * 0.8 + latency_ms * 0.2

    def record_failure(self):
        """Increment the failure counter and mark unhealthy if threshold is hit."""

        self._failures += 1
        self._last_failure_time = time.monotonic()
        self._total_requests += 1
        if self._failures >= self.max_failures:
            self._healthy = False
            logger.warning(
                "[RPC] Marked unhealthy (%s failures): %s",
                self._failures,
                self.url,
            )

    def stats(self) -> dict:
        """Return a snapshot of endpoint health and request statistics."""
        return {
            "url": self.url,
            "type": self.provider_type.value,
            "healthy": self._healthy,
            "failures": self._failures,
            "total_requests": self._total_requests,
            "latency_ms": round(self._latency_ema_ms, 2),
        }
