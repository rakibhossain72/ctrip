"""
Universal EVM-compatible blockchain client with automatic RPC failover.

Each chain can supply one RPC endpoint or a prioritised list — the client
tries them in order and rotates to the next one whenever a call fails.

chains.yaml supports both forms:

  # single endpoint (backward-compatible)
  - name: ethereum
    rpc_url: https://mainnet.infura.io/v3/KEY

  # multiple endpoints with automatic failover
  - name: ethereum
    rpc_urls:
      - https://mainnet.infura.io/v3/KEY          # primary
      - https://eth-mainnet.g.alchemy.com/v2/KEY  # fallback 1
      - https://rpc.ankr.com/eth                  # fallback 2
    chain_id: 1   # optional — auto-fetched from node if omitted
    poa: false    # set true for BSC, Polygon, etc.
"""

import json
import logging
import pathlib
import time
from typing import Any, Dict, List, Optional

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


def _make_w3(url: str, poa: bool, timeout: int) -> AsyncWeb3:
    """Create an AsyncWeb3 instance for *url*."""
    w3 = AsyncWeb3(AsyncHTTPProvider(url, request_kwargs={"timeout": timeout}))
    if poa:
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


class EVMClient:
    """
    Generic async EVM client that works with any EVM-compatible chain.

    Accepts one or more RPC URLs. When a call raises an exception the client
    immediately retries on the next URL in the list (round-robin). After all
    URLs have been tried once the exception is re-raised so the caller can
    decide how to handle it.

    Parameters
    ----------
    rpc_urls:
        Ordered list of RPC endpoints. The first URL is used by default;
        later ones are fallbacks.
    chain_id:
        Optional chain ID override. Fetched lazily from the active node
        when first needed.
    poa:
        Inject ExtraDataToPOAMiddleware for PoA networks (BSC, Polygon …).
    request_timeout:
        Per-request RPC timeout in seconds.
    """

    def __init__(
        self,
        rpc_urls: List[str],
        chain_id: Optional[int] = None,
        poa: bool = False,
        request_timeout: int = 30,
    ):
        if not rpc_urls:
            raise ValueError("At least one RPC URL must be provided")

        self.rpc_urls = list(rpc_urls)
        self._chain_id = chain_id
        self.poa = poa
        self._timeout = request_timeout
        self._active_index = 0

        # Build a web3 instance for every URL up front so we can swap instantly
        self._w3_pool: List[AsyncWeb3] = [
            _make_w3(url, poa, request_timeout) for url in self.rpc_urls
        ]

        self._gas_price_cache: Optional[int] = None
        self._gas_price_ts: float = 0.0
        self._gas_cache_ttl: int = 10  # seconds

    # Active web3 instance

    @property
    def w3(self) -> AsyncWeb3:
        """The currently active AsyncWeb3 instance."""
        return self._w3_pool[self._active_index]

    @property
    def provider_url(self) -> str:
        """URL of the currently active RPC endpoint."""
        return self.rpc_urls[self._active_index]

    def _rotate(self) -> bool:
        """
        Advance to the next RPC URL.
        Returns True if a new URL is now active, False if we have wrapped
        back to the start (all endpoints exhausted in this attempt).
        """
        next_index = (self._active_index + 1) % len(self.rpc_urls)
        rotated = next_index != 0 or len(self.rpc_urls) == 1
        self._active_index = next_index
        if next_index != 0:
            logger.warning(
                "RPC failover: switching to endpoint [%d/%d] %s",
                next_index + 1,
                len(self.rpc_urls),
                self.rpc_urls[next_index],
            )
        return next_index != 0

    async def _call_with_failover(self, fn, *args, **kwargs):
        """
        Call *fn* (a coroutine function bound to self) with automatic failover.

        Tries every URL in the pool exactly once. Raises the last exception
        if none of them succeed.
        """
        start_index = self._active_index
        last_exc: Optional[Exception] = None

        for attempt in range(len(self.rpc_urls)):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                last_exc = exc
                logger.warning(
                    "RPC call failed on %s (attempt %d/%d): %s",
                    self.provider_url,
                    attempt + 1,
                    len(self.rpc_urls),
                    exc,
                )
                # Rotate only when there are more endpoints to try
                if attempt < len(self.rpc_urls) - 1:
                    self._active_index = (start_index + attempt + 1) % len(
                        self.rpc_urls
                    )
                    logger.warning(
                        "Failing over to endpoint [%d/%d]: %s",
                        self._active_index + 1,
                        len(self.rpc_urls),
                        self.provider_url,
                    )

        raise last_exc  # type: ignore[misc]

    # Chain ID

    async def get_chain_id(self) -> int:
        """Return the chain ID, fetching it from the node if not known."""
        if self._chain_id is None:
            self._chain_id = await self._call_with_failover(
                lambda: self.w3.eth.chain_id
            )
        return self._chain_id

    # Connectivity

    async def is_connected(self) -> bool:
        """Return True if at least one RPC endpoint is reachable."""
        for i, w3 in enumerate(self._w3_pool):
            try:
                if await w3.is_connected():
                    if i != self._active_index:
                        logger.info(
                            "Connectivity check: switching active endpoint to [%d/%d] %s",
                            i + 1,
                            len(self.rpc_urls),
                            self.rpc_urls[i],
                        )
                        self._active_index = i
                    return True
            except Exception:  # pylint: disable=broad-exception-caught
                pass
        return False

    # Balances

    async def get_balance(self, address: str) -> int:
        """Native token balance in wei."""
        cs = AsyncWeb3.to_checksum_address(address)
        return await self._call_with_failover(lambda: self.w3.eth.get_balance(cs))

    async def get_token_balance(self, token_address: str, wallet_address: str) -> int:
        """ERC-20 token balance in base units."""

        async def _call():
            contract = self.w3.eth.contract(
                address=AsyncWeb3.to_checksum_address(token_address),
                abi=ERC20_ABI,
            )
            return await contract.functions.balanceOf(
                AsyncWeb3.to_checksum_address(wallet_address)
            ).call()

        return await self._call_with_failover(_call)

    # Gas

    async def get_gas_price(self, use_cache: bool = True) -> int:
        """Legacy gas price with optional short-lived cache."""
        if use_cache and self._gas_price_cache is not None:
            if time.time() - self._gas_price_ts < self._gas_cache_ttl:
                return self._gas_price_cache

        price = await self._call_with_failover(lambda: self.w3.eth.gas_price)

        if use_cache:
            self._gas_price_cache = price
            self._gas_price_ts = time.time()

        return price

    async def get_fee_history(self, block_count: int = 5, newest_block: str = "latest"):
        """EIP-1559 fee history."""
        return await self._call_with_failover(
            lambda: self.w3.eth.fee_history(block_count, newest_block, [25, 50, 75])
        )

    async def estimate_gas(self, tx: Dict[str, Any]) -> int:
        """Estimate gas, falling back to a safe default on error."""
        try:
            return await self._call_with_failover(lambda: self.w3.eth.estimate_gas(tx))
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning(
                "Gas estimation failed on all endpoints, using default: %s", exc
            )
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
        """Construct a signed-ready transaction dict, preferring EIP-1559."""
        from_cs = AsyncWeb3.to_checksum_address(from_address)

        if nonce is None:
            nonce = await self._call_with_failover(
                lambda: self.w3.eth.get_transaction_count(from_cs, "pending")
            )

        tx: Dict[str, Any] = {
            "nonce": nonce,
            "from": from_cs,
            "to": AsyncWeb3.to_checksum_address(to_address),
            "value": value_wei,
            "data": data,
            "chainId": await self.get_chain_id(),
        }

        try:
            history = await self.get_fee_history()
            base_fee = history["baseFeePerGas"][-1]
            priority_fee = history["reward"][-1][1]
            tx["maxFeePerGas"] = int(base_fee * 2 + priority_fee)
            tx["maxPriorityFeePerGas"] = priority_fee
        except Exception:  # pylint: disable=broad-exception-caught
            tx["gasPrice"] = await self.get_gas_price()

        tx["gas"] = int((gas_limit or await self.estimate_gas(tx)) * 1.1)
        return tx

    async def send_transaction(self, tx: Dict[str, Any], private_key: str) -> str:
        """Sign and broadcast a transaction; returns the hex tx hash."""
        Account.from_key(private_key)  # validates key early
        signed = self.w3.eth.account.sign_transaction(tx, private_key)

        async def _send():
            return await self.w3.eth.send_raw_transaction(signed.raw_transaction)

        tx_hash = await self._call_with_failover(_send)
        return AsyncWeb3.to_hex(tx_hash)

    async def get_receipt(self, tx_hash: str, timeout: int = 120) -> Any:
        """Wait for and return the transaction receipt."""
        return await self._call_with_failover(
            lambda: self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)
        )

    # Block helpers

    async def get_latest_block(self) -> int:
        """Return the latest block number."""
        return await self._call_with_failover(lambda: self.w3.eth.block_number)

    # Repr

    def __repr__(self) -> str:
        active = self.rpc_urls[self._active_index]
        return (
            f"EVMClient(active={active!r}, "
            f"total_endpoints={len(self.rpc_urls)}, "
            f"chain_id={self._chain_id!r}, poa={self.poa})"
        )
