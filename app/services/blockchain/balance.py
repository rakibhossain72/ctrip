import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, DefaultDict
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from web3 import AsyncWeb3
from web3_multi_provider import AsyncMultiProvider

from app.blockchain.multicall import Multicall
from app.db.models.payment import Payment, PaymentStatus
from app.services.blockchain.common import get_chains
from app.core.logger import logger

POLL_INTERVAL = 5


# Chain Client
@dataclass
class ChainClient:
    chain: str
    provider: AsyncMultiProvider
    w3: AsyncWeb3

    @classmethod
    def from_rpc_urls(cls, chain: str, urls: List[str]) -> "ChainClient":
        provider = AsyncMultiProvider(urls)
        return cls(chain=chain, provider=provider, w3=AsyncWeb3(provider))


# Processor
@dataclass
class PaymentProcessor:
    session: AsyncSession
    rpcs: Dict = field(default_factory=get_chains)
    _clients: Dict[str, ChainClient] = field(default_factory=dict)

    # DB Layer
    async def _pending_payments(self, chain: str) -> List[Payment]:
        result = await self.session.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.PENDING,
                Payment.chain == chain,
            )
        )
        return result.scalars().all()

    # RPC Client
    def _get_client(self, chain: str) -> ChainClient | None:
        if chain in self._clients:
            return self._clients[chain]

        urls = self.rpcs.get(chain, {}).get("https")
        if not urls:
            logger.warning("Missing RPC URLs for chain: %s", chain)
            return None

        client = ChainClient.from_rpc_urls(chain, urls)
        self._clients[chain] = client
        return client

    # Grouping (no RPC here)
    def _group_payments(
        self, payments: List[Payment]
    ) -> Tuple[List[str], DefaultDict[str, List[str]]]:

        eth_addresses: List[str] = []
        token_map: DefaultDict[str, List[str]] = defaultdict(list)

        for p in payments:
            if p.token_contract_address:
                token_map[p.token_contract_address].append(p.address)
            else:
                eth_addresses.append(p.address)

        return eth_addresses, token_map

    # Balance fetchers
    async def _fetch_native_balances(self, multicall: Multicall, addresses: List[str]):
        if not addresses:
            return {}

        return await multicall.get_native_balances(addresses)

    async def _fetch_token_balances(
        self,
        multicall: Multicall,
        token_map: Dict[str, List[str]],
    ):
        if not token_map:
            return {}

        tasks = [
            multicall.get_erc20_balances(contract, addresses)
            for contract, addresses in token_map.items()
        ]

        return await asyncio.gather(*tasks)

    # Main logic
    async def confirm_by_balance(self, chain: str):
        payments = await self._pending_payments(chain)

        if not payments:
            logger.info("No pending payments on %s", chain)
            return None

        client = self._get_client(chain)
        if not client:
            return None

        multicall = Multicall(client.w3)

        eth_addresses, token_map = self._group_payments(payments)

        # Run native + token calls in parallel
        native_task = self._fetch_native_balances(multicall, eth_addresses)
        token_task = self._fetch_token_balances(multicall, token_map)

        native_balances, token_balances = await asyncio.gather(
            native_task,
            token_task,
        )

        return {
            "native": native_balances,
            "tokens": token_balances,
        }


# Runner
async def main():
    from app.db.async_session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        processor = PaymentProcessor(session)

        while True:
            try:
                # You can later parallelize chains here
                await processor.confirm_by_balance("anvil")

            except Exception:
                logger.exception("Payment loop crashed")

            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
