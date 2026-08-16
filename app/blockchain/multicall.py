"""
Batch EVM call execution via Multicall3 or raw JSON-RPC batch requests.
"""

import asyncio
from typing import Any

import aiohttp
from eth_abi import decode
from eth_utils import to_checksum_address
from web3 import AsyncWeb3

from app.blockchain.ABI import get_erc20_abi, get_multicall_abi
from app.blockchain.manager import get_w3


class Multicall:
    """Batch EVM calls using Multicall3 aggregate3 or JSON-RPC batch fallback."""

    DEFAULT_BATCH_SIZE = 100

    def __init__(
        self,
        w3: AsyncWeb3,
        multicall_address: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ):
        self.w3 = w3
        self.batch_size = batch_size
        self._use_multicall = multicall_address is not None

        if self._use_multicall:
            self.address = to_checksum_address(multicall_address)
            self.contract = w3.eth.contract(
                address=self.address,
                abi=get_multicall_abi(),
            )
        else:
            self.address = None
            self.contract = None

        # Dummy ERC-20 instance for ABI encoding only
        self._erc20_encoder = w3.eth.contract(abi=get_erc20_abi())

    #  Internal: aggregate3 engine
    async def _execute_aggregate3(
        self, calls: list[dict[str, Any]]
    ) -> list[tuple[bool, bytes]]:
        """Run calls through the Multicall3 contract, respecting batch_size."""
        if self.contract is None:
            raise RuntimeError("Multicall contract address was not provided.")

        results: list[tuple[bool, bytes]] = []

        for i in range(0, len(calls), self.batch_size):
            chunk = calls[i : i + self.batch_size]
            payload = [
                (
                    to_checksum_address(c["target"]),
                    c.get("allow_failure", True),
                    c["data"],
                )
                for c in chunk
            ]
            chunk_results = await self.contract.functions.aggregate3(payload).call()
            results.extend(chunk_results)

        return results

    #  Internal: RPC batch engine
    async def _execute_rpc_batch(
        self,
        calls: list[dict[str, Any]],
        block: str = "latest",
    ) -> list[bytes | None]:
        """Send calls as JSON-RPC batch requests, respecting batch_size."""
        rpc_url = str(self.w3.provider.endpoint_uri)
        all_results: list[bytes | None] = [None] * len(calls)

        async with aiohttp.ClientSession() as session:
            for chunk_start in range(0, len(calls), self.batch_size):
                chunk = calls[chunk_start : chunk_start + self.batch_size]

                batch = [
                    {
                        "jsonrpc": "2.0",
                        # id encodes the absolute index so we can place
                        # results correctly even if chunks run concurrently
                        "id": chunk_start + local_idx,
                        "method": "eth_call",
                        "params": [
                            {
                                "to": to_checksum_address(c["target"]),
                                "data": (
                                    c["data"].hex()
                                    if isinstance(c["data"], (bytes, bytearray))
                                    else c["data"]
                                ),
                            },
                            block,
                        ],
                    }
                    for local_idx, c in enumerate(chunk)
                ]

                async with session.post(
                    rpc_url,
                    json=batch,
                    headers={"Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    chunk_responses: list[dict] = await response.json()

                # Results may arrive out of order within a chunk
                for resp in chunk_responses:
                    abs_idx: int = resp["id"]
                    if "error" in resp or "result" not in resp:
                        all_results[abs_idx] = None
                    else:
                        hex_result: str = resp["result"]
                        all_results[abs_idx] = (
                            bytes.fromhex(hex_result.removeprefix("0x"))
                            if hex_result and hex_result != "0x"
                            else None
                        )

        return all_results

    #  Public: unified execute — picks the right engine automatically
    async def execute(
        self,
        calls: list[dict[str, Any]],
        block: str = "latest",
    ) -> list[tuple[bool, bytes | None]]:
        """Execute calls via aggregate3 when available, else RPC batch.

        Always returns ``[(success, data), ...]`` regardless of path so
        callers never need to branch on the engine used.
        """
        if self._use_multicall:
            # aggregate3 already returns (success, bytes) tuples
            return await self._execute_aggregate3(calls)

        # Normalise RPC batch results to the same tuple shape.
        # We have no per-call revert info from RPC, so treat
        # a None result (node error / empty return) as failure.
        raw = await self._execute_rpc_batch(calls, block=block)
        return [(data is not None, data or b"") for data in raw]

    #  Public: balance helpers
    async def get_native_balances(self, addrs: list[str]) -> list[list]:
        """Return [[address, balance_wei], ...] for native token balances."""
        valid_addresses: list[str] = []
        calls: list[dict[str, Any]] = []

        for address in addrs:
            try:
                checksummed = to_checksum_address(address)

                if self._use_multicall:
                    # getEthBalance is a Multicall3 helper function
                    call_data = self.contract.encode_abi(
                        "getEthBalance", args=[checksummed]
                    )
                    target = self.address
                else:
                    # eth_getBalance isn't an eth_call; use a raw
                    # balanceOf-style call via a minimal proxy instead.
                    # For native balance without Multicall3 the cleanest
                    # approach is a direct eth_getBalance RPC call per
                    # address — we do that concurrently here.
                    valid_addresses.append(address)
                    continue

                calls.append(
                    {"target": target, "allow_failure": True, "data": call_data}
                )
                valid_addresses.append(address)
            except ValueError:
                continue

        # Fast path: no Multicall3 => use concurrent eth_getBalance calls
        if not self._use_multicall:
            if not valid_addresses:
                return []
            balances_raw = await asyncio.gather(
                *[
                    self.w3.eth.get_balance(to_checksum_address(a))
                    for a in valid_addresses
                ]
            )
            return [[addr, bal] for addr, bal in zip(valid_addresses, balances_raw)]

        if not calls:
            return []

        results = await self.execute(calls)

        balances: list[list] = []
        for address, (success, data) in zip(valid_addresses, results):
            balance = decode(["uint256"], data)[0] if success and data else 0
            balances.append([address, balance])

        return balances

    async def get_erc20_balances(
        self, token_address: str, addrs: list[str]
    ) -> list[list]:
        """Return [[address, balance_raw], ...] for an ERC-20 token."""
        token_checksummed = to_checksum_address(token_address)
        valid_addresses: list[str] = []
        calls: list[dict[str, Any]] = []

        for address in addrs:
            try:
                checksummed = to_checksum_address(address)
                call_data = self._erc20_encoder.encode_abi(
                    "balanceOf", args=[checksummed]
                )
                calls.append(
                    {
                        "target": token_checksummed,
                        "allow_failure": True,
                        "data": call_data,
                    }
                )
                valid_addresses.append(address)
            except ValueError:
                continue

        if not calls:
            return []

        results = await self.execute(calls)

        balances: list[list] = []
        for address, (success, data) in zip(valid_addresses, results):
            balance = decode(["uint256"], data)[0] if success and data else 0
            balances.append([address, balance])

        return balances


async def main():
    """Demo the Multicall helper against Sepolia."""
    sepolia_multicall = "0xcA11bde05977b3631167028862bE2a173976CA11"
    link_token_sepolia = "0x779877A7B0D9E8603169DdbD7836e478b4624789"

    w3 = get_w3("sepolia")

    addresses = [
        "0xE0baF428C5C14424631286d13d684b896471553D",
        "0xD538d990E689EC4e5AD7Ef05db712c910D05CB3B",
        "0x36F39c24F7F6797Ec085081ae8D1292e4d0f3D48",
    ]

    #  With Multicall3 contract, batch_size=50
    mc = Multicall(w3, multicall_address=sepolia_multicall, batch_size=50)

    eth_balances = await mc.get_native_balances(addresses)
    print(" Native Balances (aggregate3, batch=50) ")
    for addr, bal in eth_balances:
        print(f"  {addr}  {bal / 10**18:.6f} sETH")

    erc20_balances = await mc.get_erc20_balances(link_token_sepolia, addresses)
    print("\n ERC-20 Balances (aggregate3, batch=50) ")
    for addr, bal in erc20_balances:
        print(f"  {addr}  {bal / 10**18:.6f} LINK")

    #  Without Multicall3 => auto-fallback to RPC batch
    mc_fallback = Multicall(w3, batch_size=50)  # no multicall_address

    eth_balances_fb = await mc_fallback.get_native_balances(addresses)
    print("\n Native Balances (RPC batch fallback, batch=50) ")
    for addr, bal in eth_balances_fb:
        print(f"  {addr}  {bal / 10**18:.6f} sETH")

    erc20_balances_fb = await mc_fallback.get_erc20_balances(
        link_token_sepolia, addresses
    )
    print("\n ERC-20 Balances (RPC batch fallback, batch=50) ")
    for addr, bal in erc20_balances_fb:
        print(f"  {addr}  {bal / 10**18:.6f} LINK")


if __name__ == "__main__":
    asyncio.run(main())
