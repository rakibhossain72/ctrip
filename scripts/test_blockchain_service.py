import asyncio
from scanner.blockchain_service import BlockchainService




async def main():
    service = BlockchainService()


    # get chains
    print("Enabled chains:", [chain.name for chain in service.enabled_chains])

    # connect to chains
    await service.connections.connect_all()

    # get block number for each chain
    for chain_id, w3 in service.w3s.items():
        block_number = await w3.eth.block_number
        print(f"Chain {chain_id} block number: {block_number}")

    # get block data and logs for each chain
    for chain_id, w3 in service.w3s.items():
        block_number = await w3.eth.block_number
        block_data = await w3.eth.get_block(block_number, full_transactions=True)
        print(f"Chain {chain_id} block transactions: {len(block_data['transactions'])}")
        if block_data['transactions']:
            tx = block_data['transactions'][0]
            print(f"  First tx: {tx.hash.hex()}")
        

        # logs
        logs = await service.get_erc20_transfer_logs(
            chain_id,
            from_block=block_number - 10,
            to_block=block_number,
        )
        print(f"Chain {chain_id} logs: {len(logs)}")
        if logs:
            print(f"  First log: {logs[0].transactionHash.hex()}")

    
    
    # get last scanned blocks
    # print("Last scanned blocks:", service.last_scanned_blocks)

    # close connections
    await service.connections.close_all()


if __name__ == "__main__":
    asyncio.run(main())