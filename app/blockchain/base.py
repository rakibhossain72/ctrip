"""
Base class for blockchain interactions.
"""
import logging
import time
import json
import pathlib
from typing import Any, Dict, Optional

from eth_account import Account
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers import AsyncHTTPProvider

logger = logging.getLogger(__name__)

with open(
    pathlib.Path(__file__).parent / "ABI/ERC20.json",
    "r",
    encoding="utf-8"
) as f:
    ERC20_ABI = json.load(f)


class BlockchainBase:
    """
    Base class providing common blockchain operations.
    """
    def __init__(
        self,
        provider_url: str,
        chain_id: Optional[int] = None,
        use_poa: bool = False,
        request_timeout: int = 30,
    ):
        self.provider_url = provider_url
        self.chain_id = chain_id
        self.use_poa = use_poa

        self.w3 = AsyncWeb3(
            AsyncHTTPProvider(provider_url, request_kwargs={"timeout": request_timeout})
        )

        if use_poa:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self._gas_price_cache = None
        self._gas_price_timestamp = 0
        self._gas_cache_duration = 10

    async def is_connected(self) -> bool:
        """Check if the web3 provider is connected."""
        try:
            return await self.w3.is_connected()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error("Failed to connect to %s: %s", self.provider_url, e)
            return False

    async def get_balance(self, address: str) -> int:
        """Get native balance in wei."""
        return await self.w3.eth.get_balance(AsyncWeb3.to_checksum_address(address))

    async def get_token_balance(self, token_address: str, user_address: str) -> int:
        """Get ERC20 token balance in base units."""
        contract = self.w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(token_address), abi=ERC20_ABI
        )
        return await contract.functions.balanceOf(
            AsyncWeb3.to_checksum_address(user_address)
        ).call()

    async def get_gas_price(self, use_cache: bool = True) -> int:
        """Get current gas price, optionally using a local cache."""
        if use_cache:
            current_time = time.time()
            if (
                self._gas_price_cache is not None
                and current_time - self._gas_price_timestamp < self._gas_cache_duration
            ):
                return self._gas_price_cache

        gas_price = await self.w3.eth.gas_price

        if use_cache:
            self._gas_price_cache = gas_price
            self._gas_price_timestamp = time.time()

        return gas_price

    async def get_fee_history(self, block_count: int = 5, newest_block: str = "latest"):
        """Fetch EIP-1559 fee history."""
        return await self.w3.eth.fee_history(block_count, newest_block, [25, 50, 75])

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas for a transaction."""
        try:
            return await self.w3.eth.estimate_gas(tx)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Gas estimation failed, using default: %s", e)
            return 21000 if not tx.get("data") else 100000

    # pylint: disable=too-many-arguments,too-many-positional-arguments
    async def build_transaction(
        self,
        from_address: str,
        to_address: str,
        value_wei: int,
        data: bytes = b"",
        gas_limit: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build a transaction dictionary."""
        from_checksum = AsyncWeb3.to_checksum_address(from_address)

        if nonce is None:
            nonce = await self.w3.eth.get_transaction_count(from_checksum, "pending")

        tx = {
            "nonce": nonce,
            "from": from_checksum,
            "to": AsyncWeb3.to_checksum_address(to_address),
            "value": value_wei,
            "data": data,
            "chainId": self.chain_id or await self.w3.eth.chain_id,
        }

        # Try EIP-1559
        try:
            fee_history = await self.get_fee_history()
            base_fee = fee_history["baseFeePerGas"][-1]
            priority_fee = fee_history["reward"][-1][1]  # median reward

            tx["maxFeePerGas"] = int((base_fee * 2) + priority_fee)
            tx["maxPriorityFeePerGas"] = priority_fee
        except Exception:  # pylint: disable=broad-exception-caught
            # Fallback to legacy gas price
            tx["gasPrice"] = await self.get_gas_price()

        if gas_limit is None:
            gas_limit = await self.estimate_gas(tx)

        tx["gas"] = int(gas_limit * 1.1)  # 10% buffer

        return tx

    async def send_transaction(self, tx: Dict[str, Any], private_key: str) -> str:
        """Sign and send a transaction."""
        # pylint: disable=no-value-for-parameter
        Account.from_key(private_key)
        signed_tx = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        return AsyncWeb3.to_hex(tx_hash)

    async def get_receipt(self, tx_hash: str, timeout: int = 120) -> Any:
        """Get transaction receipt with timeout."""
        return await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    async def get_latest_block(self) -> int:
        """Get the latest block number."""
        return await self.w3.eth.block_number
