"""
Quick smoke test for the BlockchainService wrapper.
"""

import asyncio

from scanner.blockchain_service import BlockchainService


async def main():
    """Instantiate the service and print a few health checks."""
    service = BlockchainService()

    for chain_id in sorted(service._clients):  # pylint: disable=protected-access
        print(f"Chain {chain_id} block number: {await service.get_current_block(chain_id)}")

    chain_id = next(iter(service._clients))  # pylint: disable=protected-access
    block_number = await service.get_current_block(chain_id)
    txs = await service.get_block_transactions(chain_id, block_number)
    print(f"Chain {chain_id} block {block_number} transactions: {len(txs)}")

    logs = await service.get_transfer_logs(
        chain_id,
        from_block=block_number - 10,
        to_block=block_number,
    )
    print(f"Chain {chain_id} transfer logs: {len(logs)}")

    await service.close()


if __name__ == "__main__":
    asyncio.run(main())
