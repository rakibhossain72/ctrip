from __future__ import annotations

from typing import Optional, Iterable

from web3.types import BlockData, LogReceipt

from app.core.logger import listener_logger as log
from app.blockchain.ABI import get_erc20_abi
from app.workers.utils import get_enabled_chains
from scanner.blockchain_service.log_scanner import LogScanner

from .connection import ChainConnectionManager
from .retry import RetryPolicy
from .block_reader import BlockReader
from .constants import MAX_RETRIES, RETRY_BACKOFF


class BlockchainService:
    """High-level service for interacting with multiple blockchains."""

    def __init__(self) -> None:
        self.connections = ChainConnectionManager(get_enabled_chains())
        self.retry_policy = RetryPolicy(MAX_RETRIES, RETRY_BACKOFF)
        self.block_reader = BlockReader(self.connections, self.retry_policy)
        self.log_scanner = LogScanner(self.connections, self.retry_policy)
        self.erc20_abi = self._load_erc20_abi()
        self.last_scanned_blocks: dict[int, int] = {}

    # Backwards-compatible passthroughs
    @property
    def w3s(self):
        return self.connections.w3s

    @property
    def chains_by_id(self):
        return self.connections.chains_by_id

    @property
    def enabled_chains(self):
        return self.connections.enabled_chains

    # Lifecycle
    async def __aenter__(self) -> "BlockchainService":
        await self.connect_to_chains()
        return self

    async def __aexit__(self, *_exc_info) -> None:
        await self.close()

    async def connect_to_chains(self) -> None:
        await self.connections.connect_all()

    async def close(self) -> None:
        await self.connections.close_all()

    # ABI
    @staticmethod
    def _load_erc20_abi():
        try:
            return get_erc20_abi()
        except Exception:
            log.exception("Failed to load ERC20 ABI")
            raise

    # Block reads
    async def get_block_number(self, chain_id: int) -> Optional[int]:
        return await self.block_reader.get_block_number(chain_id)

    async def get_block(self, chain_id: int, block_number: int) -> Optional[BlockData]:
        return await self.block_reader.get_block(chain_id, block_number)

    # Log scanning
    async def get_logs(
        self,
        chain_id: int,
        *,
        from_block: int,
        to_block: int,
        address: Optional[list[str]] = None,
        topics: Optional[list] = None,
    ) -> Optional[list[LogReceipt]]:
        return await self.log_scanner.get_logs(
            chain_id,
            from_block=from_block,
            to_block=to_block,
            address=address,
            topics=topics,
        )

    async def get_erc20_transfer_logs(
        self,
        chain_id: int,
        *,
        from_block: int,
        to_block: int,
        token_addresses: Optional[Iterable[str]] = None,
        sender_addresses: Optional[Iterable[str]] = None,
        receiver_addresses: Optional[Iterable[str]] = None,
    ) -> Optional[list[LogReceipt]]:
        return await self.log_scanner.get_erc20_transfer_logs(
            chain_id,
            from_block=from_block,
            to_block=to_block,
            token_addresses=token_addresses,
            sender_addresses=sender_addresses,
            receiver_addresses=receiver_addresses,
        )
