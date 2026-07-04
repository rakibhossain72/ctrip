from __future__ import annotations

import asyncio
from typing import Optional

from web3 import AsyncWeb3
from web3.providers.rpc import AsyncHTTPProvider

from app.core.logger import listener_logger as log
from app.workers.utils import Chain


class ChainConnectionManager:
    """Owns the lifecycle of AsyncWeb3 connections for a set of chains."""

    def __init__(self, enabled_chains: list[Chain] = None) -> None:
        self.enabled_chains: list[Chain] = enabled_chains
        self.w3s: dict[int, AsyncWeb3] = {}
        self.chains_by_id: dict[int, Chain] = {}

    async def connect_all(self) -> None:
        results = await asyncio.gather(
            *(self._connect_one(chain) for chain in self.enabled_chains),
            return_exceptions=True,
        )
        for chain, result in zip(self.enabled_chains, results):
            if isinstance(result, Exception):
                log.error(f"Error connecting to {chain.name}: {result}")

    async def _connect_one(self, chain: Chain) -> None:
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(chain.http_url))
            if not await w3.is_connected():
                log.error(f"Failed to connect to {chain.name} at {chain.http_url}")
                return
            self.w3s[chain.chain_id] = w3
            self.chains_by_id[chain.chain_id] = chain
            log.info(f"Connected to {chain.name} (chain_id={chain.chain_id})")
        except Exception:
            log.exception(f"Error connecting to {chain.name}")
            raise

    async def close_all(self) -> None:
        for chain_id, w3 in self.w3s.items():
            provider = w3.provider
            disconnect = getattr(provider, "disconnect", None)
            if disconnect is not None:
                try:
                    await disconnect()
                except Exception:
                    log.warning(
                        f"Error disconnecting provider for chain {chain_id}",
                        exc_info=True,
                    )
        self.w3s.clear()

    def get(self, chain_id: int) -> Optional[AsyncWeb3]:
        w3 = self.w3s.get(chain_id)
        if not w3:
            log.error(f"No web3 instance for chain {chain_id}")
        return w3

    def chain_name(self, chain_id: int) -> str:
        chain = self.chains_by_id.get(chain_id)
        return chain.name if chain else str(chain_id)
