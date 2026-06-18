"""
Universal EVM-compatible blockchain client.

Configured entirely from chains.yaml — no per-chain subclasses needed.
Each chain entry can specify:
  - name:     identifier (e.g. ethereum, bsc, anvil)
  - rpc_url:  HTTP or WebSocket RPC endpoint
  - chain_id: (optional) override; auto-fetched from the node if omitted
  - poa:      (optional, bool) inject PoA middleware for chains like BSC
"""

import json
import logging
import pathlib
import time
from typing import Any, Dict, Optional

from eth_account import Account
from web3 import AsyncWeb3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers import AsyncHTTPProvider

logger = logging.getLogger(__name__)

with open(
    pathlib.Path(__file__).parent / "ABI/ERC20.json",
    encoding="utf-8",
) as _f:
    ERC20_ABI = json.load(_f)


class EVMClient:
    """
    Generic async EVM client. Works with any EVM-compatible chain.

    Parameters:

    provider_url:
        HTTP(S) or WS(S) RPC endpoint.
    chain_id:
        Chain ID override. When None the value is lazily fetched from the node
        the first time it is needed (e.g. for transaction signing).
    poa:
        Set True for PoA networks (BSC, Polygon, …) to inject the
        ExtraDataToPOAMiddleware that tolerates oversized block headers.
    request_timeout:
        Seconds before an RPC call times out.
    """

    def __init__(
        self,
        provider_url: str,
        chain_id: Optional[int] = None,
        poa: bool = False,
        request_timeout: int = 30,
    ):
        self.provider_url = provider_url
        self._chain_id = chain_id
        self.poa = poa

        self.w3 = AsyncWeb3(
            AsyncHTTPProvider(provider_url, request_kwargs={"timeout": request_timeout})
        )

        if poa:
            self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

        self._gas_price_cache: Optional[int] = None
        self._gas_price_ts: float = 0.0
        self._gas_cache_ttl: int = 10  # seconds

    # Chain ID

    async def get_chain_id(self) -> int:
        """Return the chain ID, fetching it from the node if not already known."""
        if self._chain_id is None:
            self._chain_id = await self.w3.eth.chain_id
        return self._chain_id

    # Connectivity

    async def is_connected(self) -> bool:
        try:
            return await self.w3.is_connected()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.error("Connection check failed for %s: %s", self.provider_url, exc)
            return False

    # Balances

    async def get_balance(self, address: str) -> int:
        """Native token balance in wei."""
        return await self.w3.eth.get_balance(AsyncWeb3.to_checksum_address(address))

    async def get_token_balance(self, token_address: str, wallet_address: str) -> int:
        """ERC-20 token balance in base units."""
        contract = self.w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(token_address),
            abi=ERC20_ABI,
        )
        return await contract.functions.balanceOf(
            AsyncWeb3.to_checksum_address(wallet_address)
        ).call()

    # Gas

    async def get_gas_price(self, use_cache: bool = True) -> int:
        """Legacy gas price, with an optional short-lived in-memory cache."""
        if use_cache and self._gas_price_cache is not None:
            if time.time() - self._gas_price_ts < self._gas_cache_ttl:
                return self._gas_price_cache

        price = await self.w3.eth.gas_price

        if use_cache:
            self._gas_price_cache = price
            self._gas_price_ts = time.time()

        return price

    async def get_fee_history(self, block_count: int = 5, newest_block: str = "latest"):
        """EIP-1559 fee history (base fee + priority fee percentiles)."""
        return await self.w3.eth.fee_history(block_count, newest_block, [25, 50, 75])

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas for a transaction, falling back to a safe default."""
        try:
            return await self.w3.eth.estimate_gas(tx)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Gas estimation failed, using default: %s", exc)
            return 21000 if not tx.get("data") else 100_000

    # Transaction building & sending

    async def build_transaction(
        self,
        from_address: str,
        to_address: str,
        value_wei: int,
        data: bytes = b"",
        gas_limit: Optional[int] = None,
        nonce: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Construct a transaction dict, preferring EIP-1559 fees."""
        from_cs = AsyncWeb3.to_checksum_address(from_address)

        if nonce is None:
            nonce = await self.w3.eth.get_transaction_count(from_cs, "pending")

        tx: Dict[str, Any] = {
            "nonce": nonce,
            "from": from_cs,
            "to": AsyncWeb3.to_checksum_address(to_address),
            "value": value_wei,
            "data": data,
            "chainId": await self.get_chain_id(),
        }

        # Prefer EIP-1559; fall back to legacy gasPrice
        try:
            history = await self.get_fee_history()
            base_fee = history["baseFeePerGas"][-1]
            priority_fee = history["reward"][-1][1]  # median
            tx["maxFeePerGas"] = int(base_fee * 2 + priority_fee)
            tx["maxPriorityFeePerGas"] = priority_fee
        except Exception:  # pylint: disable=broad-exception-caught
            tx["gasPrice"] = await self.get_gas_price()

        tx["gas"] = int((gas_limit or await self.estimate_gas(tx)) * 1.1)

        return tx

    async def send_transaction(self, tx: Dict[str, Any], private_key: str) -> str:
        """Sign and broadcast a transaction; returns the hex tx hash."""
        Account.from_key(private_key)  # validates key
        signed = self.w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = await self.w3.eth.send_raw_transaction(signed.raw_transaction)
        return AsyncWeb3.to_hex(tx_hash)

    async def get_receipt(self, tx_hash: str, timeout: int = 120) -> Any:
        """Wait for and return the transaction receipt."""
        return await self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    # Block helpers

    async def get_latest_block(self) -> int:
        """Return the latest block number."""
        return await self.w3.eth.block_number

    # Repr

    def __repr__(self) -> str:
        return (
            f"EVMClient(url={self.provider_url!r}, "
            f"chain_id={self._chain_id!r}, poa={self.poa})"
        )
