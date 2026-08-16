"""
Async Rotating RPC Manager for web3.py v7
Supports both HTTP (AsyncHTTPProvider) and WebSocket (WebSocketProvider)
with automatic failover, health checks, and weighted round-robin rotation.

Providers (web3.py v7):
  - HTTP  -> AsyncHTTPProvider       (stateless, per-call)
  - WSS   -> WebSocketProvider       (persistent connection provider)

Subscriptions use the v7 SubscriptionManager API:
  NewHeadsSubscription, LogsSubscription, PendingTxSubscription, SyncingSubscription
"""

import asyncio
import time
from typing import Any, Callable, Optional

from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider, WebSocketProvider
from web3.utils.subscriptions import (
    EthSubscriptionHandler,
    LogsSubscription,
    NewHeadsSubscription,
    PendingTxSubscription,
    SyncingSubscription,
)

from app.core.logger import logger
from app.schemas.blockchain import ProviderType, RPCEndpoint


class RotatingRPCManager:
    """
    Async rotating RPC manager.

    Correct providers:
      HTTP -> AsyncHTTPProvider
      WSS  -> WebSocketProvider  (PersistentConnectionProvider)

    Subscriptions (WSS only) use the v7 subscription_manager API with typed
    subscription classes: NewHeadsSubscription, LogsSubscription, etc.
    """

    def __init__(
        self,
        endpoints: list[RPCEndpoint],
        max_retries: int = 3,
        retry_delay: float = 0.5,
        health_check_interval: float = 60.0,
    ):
        self._endpoints = endpoints
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._health_check_interval = health_check_interval

        self._http_eps = [e for e in endpoints if e.provider_type == ProviderType.HTTP]
        self._wss_eps = [e for e in endpoints if e.provider_type == ProviderType.WSS]

        self._http_idx = 0
        self._wss_idx = 0
        self._lock = asyncio.Lock()

        # url -> AsyncWeb3 with an active WebSocketProvider connection
        self._wss_cache: dict[str, AsyncWeb3] = {}
        self._health_task: Optional[asyncio.Task] = None

    # lifecycle

    async def start(self):
        """Start the health-check loop and initialize connections."""
        self._health_task = asyncio.create_task(self._health_loop())
        logger.info(
            "[RPC] Started — %s HTTP, %s WSS",
            len(self._http_eps),
            len(self._wss_eps),
        )

    async def stop(self):
        """Cancel the health loop and disconnect all WSS providers."""
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass

        for _, w3 in list(self._wss_cache.items()):
            try:
                await w3.provider.disconnect()
            except Exception:  # pylint: disable=broad-exception-caught
                pass
        self._wss_cache.clear()
        logger.info("[RPC] Stopped")

    async def __aenter__(self):
        """Enter async context manager."""
        await self.start()
        return self

    async def __aexit__(self, *_):
        """Exit async context manager and stop."""
        await self.stop()

    # provider selection (weighted round-robin)

    async def _pick_http(self) -> Optional[RPCEndpoint]:
        async with self._lock:
            pool = [e for e in self._http_eps if e.is_healthy for _ in range(e.weight)]
            if not pool:
                return None
            ep = pool[self._http_idx % len(pool)]
            self._http_idx += 1
            return ep

    async def _pick_wss(self) -> Optional[RPCEndpoint]:
        async with self._lock:
            pool = [e for e in self._wss_eps if e.is_healthy for _ in range(e.weight)]
            if not pool:
                return None
            ep = pool[self._wss_idx % len(pool)]
            self._wss_idx += 1
            return ep

    # HTTP calls
    async def call(self, fn: Callable[[AsyncWeb3], Any]) -> Any:
        """Run an async web3 call over HTTP with automatic rotation + retry."""
        last_exc: Exception = RuntimeError("No healthy HTTP endpoints")

        for attempt in range(self._max_retries):
            ep = await self._pick_http()
            if ep is None:
                raise RuntimeError("All HTTP endpoints are unhealthy")

            w3 = AsyncWeb3(AsyncHTTPProvider(ep.url))
            t0 = time.monotonic()
            try:
                result = await fn(w3)
                ep.record_success((time.monotonic() - t0) * 1000)
                return result
            except Exception as exc:  # pylint: disable=broad-exception-caught
                ep.record_failure()
                last_exc = exc
                logger.debug(
                    "[HTTP] attempt %s failed on %s: %s",
                    attempt + 1,
                    ep.url,
                    exc,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise last_exc

    # WSS connection cache
    async def _get_wss(self, ep: RPCEndpoint) -> AsyncWeb3:
        """Return a cached, connected AsyncWeb3 WSS instance."""
        if ep.url not in self._wss_cache:
            w3 = AsyncWeb3(WebSocketProvider(ep.url))
            await w3.provider.connect()
            self._wss_cache[ep.url] = w3
            logger.debug("[WSS] Connected: %s", ep.url)
        return self._wss_cache[ep.url]

    async def _drop_wss(self, url: str):
        """Remove a cached WSS connection from the pool."""
        w3 = self._wss_cache.pop(url, None)
        if w3:
            try:
                await w3.provider.disconnect()
            except Exception:  # pylint: disable=broad-exception-caught
                pass

    # WSS one-shot calls
    async def call_wss(self, fn: Callable[[AsyncWeb3], Any]) -> Any:
        """Run an async web3 call over WebSocket with rotation + retry."""
        last_exc: Exception = RuntimeError("No healthy WSS endpoints")

        for attempt in range(self._max_retries):
            ep = await self._pick_wss()
            if ep is None:
                raise RuntimeError("All WSS endpoints are unhealthy")

            t0 = time.monotonic()
            try:
                w3 = await self._get_wss(ep)
                result = await fn(w3)
                ep.record_success((time.monotonic() - t0) * 1000)
                return result
            except Exception as exc:  # pylint: disable=broad-exception-caught
                ep.record_failure()
                await self._drop_wss(ep.url)
                last_exc = exc
                logger.debug(
                    "[WSS] attempt %s failed on %s: %s",
                    attempt + 1,
                    ep.url,
                    exc,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay * (attempt + 1))

        raise last_exc

    # Subscriptions (web3.py v7 API)
    async def subscribe_new_heads(
        self,
        handler: EthSubscriptionHandler,
        reconnect: bool = True,
    ):
        """Subscribe to new block headers."""
        await self._subscribe(NewHeadsSubscription(handler=handler), reconnect)

    async def subscribe_logs(
        self,
        handler: EthSubscriptionHandler,
        address=None,
        topics=None,
        reconnect: bool = True,
    ):
        """Subscribe to contract logs."""
        kwargs = {}
        if address:
            kwargs["address"] = address
        if topics:
            kwargs["topics"] = topics
        await self._subscribe(LogsSubscription(handler=handler, **kwargs), reconnect)

    async def subscribe_pending_txs(
        self,
        handler: EthSubscriptionHandler,
        reconnect: bool = True,
    ):
        """Subscribe to pending transaction hashes."""
        await self._subscribe(PendingTxSubscription(handler=handler), reconnect)

    async def subscribe_syncing(
        self,
        handler: EthSubscriptionHandler,
        reconnect: bool = True,
    ):
        """Subscribe to syncing status changes."""
        await self._subscribe(SyncingSubscription(handler=handler), reconnect)

    async def _subscribe(self, subscription, reconnect: bool):
        """Internal: connect to a WSS node and run the subscription loop."""
        while True:
            ep = await self._pick_wss()
            if ep is None:
                logger.error("[WSS] No healthy endpoints for subscription")
                if not reconnect:
                    return
                await asyncio.sleep(5)
                continue

            try:
                w3 = await self._get_wss(ep)
                await w3.subscription_manager.subscribe(subscription)
                logger.info(
                    "[WSS] Subscribed %s on %s",
                    subscription.__class__.__name__,
                    ep.url,
                )
                await w3.subscription_manager.handle_subscriptions()

            except asyncio.CancelledError:
                logger.info("[WSS] Subscription task cancelled")
                return
            except Exception as exc:  # pylint: disable=broad-exception-caught
                ep.record_failure()
                await self._drop_wss(ep.url)
                logger.warning(
                    "[WSS] Subscription dropped on %s: %s",
                    ep.url,
                    exc,
                )
                if not reconnect:
                    raise
                logger.info("[WSS] Reconnecting in 2s…")
                await asyncio.sleep(2)

    # background health checks
    async def _health_loop(self):
        """Periodically ping every endpoint to update health status."""
        while True:
            await asyncio.sleep(self._health_check_interval)
            tasks = [self._ping_http(ep) for ep in self._http_eps] + [
                self._ping_wss(ep) for ep in self._wss_eps
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _ping_http(self, ep: RPCEndpoint):
        """Health-check an HTTP endpoint."""
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(ep.url))
            await asyncio.wait_for(w3.eth.chain_id, timeout=5)
            ep.record_success()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            ep.record_failure()
            logger.debug("[Health HTTP] %s: %s", ep.url, exc)

    async def _ping_wss(self, ep: RPCEndpoint):
        """Health-check a WebSocket endpoint."""
        try:
            w3 = await asyncio.wait_for(self._get_wss(ep), timeout=5)
            await asyncio.wait_for(w3.eth.chain_id, timeout=5)
            ep.record_success()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            ep.record_failure()
            await self._drop_wss(ep.url)
            logger.debug("[Health WSS] %s: %s", ep.url, exc)

    # stats
    def stats(self) -> list[dict]:
        """Return health and latency stats for every configured endpoint."""
        return [ep.stats() for ep in self._endpoints]

    def print_stats(self):
        """Print a human-readable summary of endpoint health to stdout."""
        print("\n RPC Endpoint Stats")
        for s in self.stats():
            mark = "✓" if s["healthy"] else "✗"
            print(
                f" {mark} [{s['type'].upper():4}] {s['url']:<50}"
                f"  req={s['total_requests']:>5}"
                f"  fail={s['failures']:>2}"
                f"  lat={s['latency_ms']:>7.1f}ms\n"
            )
