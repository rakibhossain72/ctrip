"""
Anvil-specific blockchain interactions for local development and testing.
"""
import logging
from typing import List, Optional

from web3 import AsyncWeb3
from app.blockchain.base import BlockchainBase

logger = logging.getLogger(__name__)


class AnvilBlockchain(BlockchainBase):
    """
    Blockchain implementation for Anvil (Foundry) with development-specific methods.
    """
    def __init__(self, provider_url: str = "http://localhost:8545", **kwargs):
        # Anvil typically has chain ID 31337
        super().__init__(provider_url, chain_id=31337, use_poa=False, **kwargs)

    async def mine_blocks(self, num_blocks: int = 1) -> List[str]:
        """Manually mine blocks in Anvil."""
        block_hashes = []
        for _ in range(num_blocks):
            result = await self.w3.provider.make_request("evm_mine", [])
            block_hashes.append(result.get("result"))
        return block_hashes

    async def set_balance(self, address: str, balance_eth: float) -> bool:
        """Set the ETH balance of an account in Anvil."""
        address_checksum = AsyncWeb3.to_checksum_address(address)
        balance_wei = AsyncWeb3.to_wei(balance_eth, "ether")
        balance_hex = hex(balance_wei)

        result = await self.w3.provider.make_request(
            "anvil_setBalance", [address_checksum, balance_hex]
        )
        return result.get("result") is not None

    async def impersonate_account(self, address: str) -> bool:
        """Tell Anvil to impersonate an account."""
        address_checksum = AsyncWeb3.to_checksum_address(address)
        result = await self.w3.provider.make_request(
            "anvil_impersonateAccount", [address_checksum]
        )
        return result.get("result") is not None

    async def stop_impersonating_account(self, address: str) -> bool:
        """Stop impersonating an account in Anvil."""
        address_checksum = AsyncWeb3.to_checksum_address(address)
        result = await self.w3.provider.make_request(
            "anvil_stopImpersonatingAccount", [address_checksum]
        )
        return result.get("result") is not None

    async def reset(
        self, forking_url: Optional[str] = None, block_number: Optional[int] = None
    ) -> bool:
        """Reset Anvil to a specific state or fork."""
        params = {}
        if forking_url:
            params["forking"] = {"jsonRpcUrl": forking_url}
            if block_number:
                params["forking"]["blockNumber"] = block_number

        result = await self.w3.provider.make_request(
            "anvil_reset", [params] if params else []
        )
        return result.get("result") is not None
