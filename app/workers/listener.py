import asyncio
import dramatiq
from web3 import AsyncWeb3
from web3.providers.rpc import AsyncHTTPProvider
from sqlalchemy import select, update
from blockchain.manager import get_blockchains
from db.session import async_session
from db.models.payment import Payment
from db.models.chain import ChainState
from core.config import settings

CONFIRMATIONS_REQUIRED = 3
BLOCK_BATCH_SIZE = 20


async def _scan_blocks():
    # w3 = AsyncWeb3(AsyncHTTPProvider(settings.RPC_URL))
    blockchains = get_blockchains()
    blockchain = blockchains["anvil"]
    w3 = AsyncWeb3(blockchain.get_async_provider())

    async with async_session() as session:
        # lock chain state row
        state = await session.execute(
            select(ChainState)
            .where(ChainState.chain == "anvil")
            .with_for_update()
        )
        state = state.scalar_one()

        latest_block = await w3.eth.block_number
        from_block = state.last_scanned_block + 1
        to_block = min(from_block + BLOCK_BATCH_SIZE, latest_block)

        if from_block > to_block:
            return

        payments = await session.execute(
            select(Payment)
            .where(Payment.status == "PENDING")
        )
        payment_map = {
            p.address.lower(): p
            for p in payments.scalars()
        }

        for block_number in range(from_block, to_block + 1):
            block = await w3.eth.get_block(block_number, full_transactions=True)

            for tx in block.transactions:
                if not tx.to:
                    continue

                addr = tx.to.lower()
                if addr not in payment_map:
                    continue

                payment = payment_map[addr]

                if tx.value < payment.amount_wei:
                    continue

                # mark as detected
                await session.execute(
                    update(Payment)
                    .where(Payment.id == payment.id)
                    .values(
                        status="DETECTED",
                        detected_tx=tx.hash.hex(),
                        detected_block=block_number,
                    )
                )

        # advance chain state
        state.last_scanned_block = to_block
        await session.commit()


async def _confirm_payments():
    blockchains = get_blockchains()
    blockchain = blockchains["anvil"]
    w3 = AsyncWeb3(blockchain.get_async_provider())
    latest_block = await w3.eth.block_number

    async with async_session() as session:
        payments = await session.execute(
            select(Payment)
            .where(Payment.status == "DETECTED")
        )

        for payment in payments.scalars():
            confirmations = latest_block - payment.detected_block

            if confirmations >= CONFIRMATIONS_REQUIRED:
                await session.execute(
                    update(Payment)
                    .where(Payment.id == payment.id)
                    .values(
                        status="CONFIRMED",
                        confirmations=confirmations,
                    )
                )

        await session.commit()


@dramatiq.actor(time_limit=10, max_retries=0)
def listen_for_payments():
    print("Listening for payments...")
    asyncio.run(_scan_blocks())
    asyncio.run(_confirm_payments())
