"""
Blockchain-facing scanning facade.

Wraps one EVMClient per configured chain, giving the scanner a small stable
surface for current block, full blocks, and ERC-20 Transfer logs.
"""

from __future__ import annotations

from typing import Iterable, Optional

from app.blockchain.chains import ChainConfig, load_chains
from app.blockchain.client import EVMClient
from scanner.constants import ERC20_TRANSFER_TOPIC
from scanner.matching import addresses_to_topics


class BlockchainService:
    """
    Blockchain-facing scanning facade.

    Wraps one `app.blockchain.client.EVMClient` per configured chain, giving
    the scanner a small, stable surface: current block, full blocks, and
    ERC-20 Transfer logs. All RPC failover/retry lives in EVMClient.
    """

    def __init__(self, chains: Iterable[ChainConfig] | None = None) -> None:
        chains = list(chains) if chains is not None else list(load_chains())
        self._clients: dict[int, EVMClient] = {
            chain.chain_id: EVMClient(
                rpc_urls=list(chain.http_urls),
                chain_id=chain.chain_id,
                poa=chain.poa,
            )
            for chain in chains
        }

    def client(self, chain_id: int) -> EVMClient:
        """Return the EVMClient for a configured chain, or raise if missing."""
        try:
            return self._clients[chain_id]
        except KeyError:
            raise ValueError(f"Chain {chain_id} is not configured") from None

    async def get_current_block(self, chain_id: int) -> int:
        """Return the latest mined block number for a chain."""
        return await self.client(chain_id).get_latest_block()

    async def get_block_transactions(
        self, chain_id: int, block_number: int
    ) -> list[dict]:
        """Return the transactions included in a specific block."""
        block = await self.client(chain_id).get_block(
            block_number, full_transactions=True
        )
        return list(block.get("transactions") or [])

    async def get_transfer_logs(
        self,
        chain_id: int,
        *,
        from_block: int,
        to_block: int,
        from_addresses: Optional[Iterable[str]] = None,
        to_addresses: Optional[Iterable[str]] = None,
        token_addresses: Optional[Iterable[str]] = None,
    ) -> list[dict]:
        """Fetch ERC-20 Transfer logs matching the given filters."""
        filter_params: dict = {"fromBlock": from_block, "toBlock": to_block}

        token_list = list(token_addresses) if token_addresses else None
        if token_list:
            filter_params["address"] = token_list

        topics: list = [ERC20_TRANSFER_TOPIC]
        from_topics = addresses_to_topics(from_addresses)
        to_topics = addresses_to_topics(to_addresses)
        if from_topics is not None or to_topics is not None:
            topics.append(from_topics)  # None here means "any sender"
            if to_topics is not None:
                topics.append(to_topics)
        filter_params["topics"] = topics

        return await self.client(chain_id).get_logs(filter_params)

    async def close(self) -> None:
        """Disconnect all cached WebSocket providers and free resources."""
        for client in self._clients.values():
            for w3 in client._w3_pool:  # pylint: disable=protected-access
                disconnect = getattr(w3.provider, "disconnect", None)
                if disconnect is not None:
                    try:
                        await disconnect()
                    except Exception:  # pylint: disable=broad-exception-caught  # pragma: no cover - best-effort cleanup
                        pass
