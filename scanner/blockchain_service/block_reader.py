from __future__ import annotations

from typing import Optional

from web3.types import BlockData

from .connection import ChainConnectionManager
from .retry import RetryPolicy


class BlockReader:
    """Reads block data from chains, with retry handling."""

    def __init__(
        self, connections: ChainConnectionManager, retry_policy: RetryPolicy
    ) -> None:
        self.connections = connections
        self.retry_policy = retry_policy

    async def get_block_number(self, chain_id: int) -> Optional[int]:
        w3 = self.connections.get(chain_id)
        if not w3:
            return None
        return await self.retry_policy.run(
            f"get_block_number({self.connections.chain_name(chain_id)})",
            lambda: w3.eth.block_number,
        )

    async def get_block(self, chain_id: int, block_number: int) -> Optional[BlockData]:
        w3 = self.connections.get(chain_id)
        if not w3:
            return None
        return await self.retry_policy.run(
            f"get_block({self.connections.chain_name(chain_id)}, {block_number})",
            lambda: w3.eth.get_block(block_number, full_transactions=True),
        )
