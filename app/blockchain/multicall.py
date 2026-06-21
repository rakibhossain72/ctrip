from typing import Any
from web3 import AsyncWeb3
from eth_abi import decode
from eth_utils import to_checksum_address

from app.blockchain.manager import get_w3
from app.blockchain.ABI import get_multicall_abi, get_erc20_abi


class Multicall:
    def __init__(self, w3: AsyncWeb3, multicall_address: str):
        self.w3 = w3
        self.address = to_checksum_address(multicall_address)
        self.contract = w3.eth.contract(
            address=self.address,
            abi=get_multicall_abi(),
        )
        
        # Instantiate a dummy contract instance just to access ERC-20 encoding helpers
        self._erc20_encoder = w3.eth.contract(abi=get_erc20_abi())

    async def execute(self, calls: list[dict[str, Any]]) -> list[tuple[bool, bytes]]:
        payload = [
            (
                to_checksum_address(call["target"]),
                call.get("allow_failure", True),
                call["data"],
            )
            for call in calls
        ]
        return await self.contract.functions.aggregate3(payload).call()

    async def get_native_balances(self, addrs: list[str]) -> list[list]:
        valid_addresses = []
        calls = []
        
        for address in addrs:
            try:
                checksummed = to_checksum_address(address)
                call_data = self.contract.encode_abi("getEthBalance", args=[checksummed])
                calls.append({"target": self.address, "allow_failure": True, "data": call_data})
                valid_addresses.append(address)
            except ValueError:
                continue

        if not calls:
            return []

        raw_results = await self.execute(calls)
        
        balances = []
        for address, (success, data) in zip(valid_addresses, raw_results):
            balance = decode(["uint256"], data)[0] if success and data else 0
            balances.append([address, balance])

        return balances

    async def get_erc20_balances(self, token_address: str, addrs: list[str]) -> list[list]:
        token_checksummed = to_checksum_address(token_address)
        valid_addresses = []
        calls = []

        for address in addrs:
            try:
                checksummed = to_checksum_address(address)
                call_data = self._erc20_encoder.encode_abi("balanceOf", args=[checksummed])
                calls.append({"target": token_checksummed, "allow_failure": True, "data": call_data})
                valid_addresses.append(address)
            except ValueError:
                continue

        if not calls:
            return []

        raw_results = await self.execute(calls)

        balances = []
        for address, (success, data) in zip(valid_addresses, raw_results):
            balance = decode(["uint256"], data)[0] if success and data else 0
            balances.append([address, balance])

        return balances


async def main():
    sepolia_multicall = "0xcA11bde05977b3631167028862bE2a173976CA11"
    link_token_sepolia = "0x779877A7B0D9E8603169DdbD7836e478b4624789" 
    
    w3 = get_w3("sepolia")
    multicall = Multicall(w3, sepolia_multicall)

    addresses = [
        "0xE0baF428C5C14424631286d13d684b896471553D",
        "0xD538d990E689EC4e5AD7Ef05db712c910D05CB3B",
        "0x36F39c24F7F6797Ec085081ae8D1292e4d0f3D48",
    ]

    # Native Balances
    eth_balances = await multicall.get_native_balances(addresses)
    print("--- Native Balances ---")
    for addr, bal in eth_balances:
        print(f"Address {addr} has {bal / 10 ** 18} sETH")

    # ERC-20 Balances
    erc20_balances = await multicall.get_erc20_balances(link_token_sepolia, addresses)
    print("\n--- ERC-20 Balances ---")
    for addr, bal in erc20_balances:
        print(f"Address {addr} has {bal / 10 ** 18} LINK")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())