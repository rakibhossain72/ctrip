import asyncio
import logging
from app.blockchain.rpc_manager.rotating_rpc import RotatingRPCManager, RPCEndpoint
from app.schemas.blockchain import ProviderType

#  Example
async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
    )

    endpoints = [
        # HTTP pool
        RPCEndpoint("https://eth-sepolia.api.onfinality.io/public", ProviderType.HTTP, weight=2),
        RPCEndpoint("https://api.zan.top/eth-sepolia", ProviderType.HTTP, weight=1),
        # # WSS pool
        RPCEndpoint("wss://mainnet.gateway.tenderly.co", ProviderType.WSS, weight=1),
    ]

    async with RotatingRPCManager(endpoints, max_retries=3) as manager:

        # HTTP calls
        block = await manager.call(lambda w3: w3.eth.get_block("latest"))
        print(f"Latest block  (HTTP): #{block['number']}")

        chain_id = await manager.call(lambda w3: w3.eth.chain_id)
        print(f"Chain ID      (HTTP): {chain_id}")

        # WSS one-shot call
        block_wss = await manager.call_wss(lambda w3: w3.eth.get_block("latest"))
        print(f"Latest block  (WSS):  #{block_wss['number']}")

        # Subscription (newHeads)
        async def block_print(block_header):
            print(f"  ↳ New block #{block_header.result.number}")

        sub_task = asyncio.create_task(
            manager.subscribe_new_heads(block_print, reconnect=True)
        )
        await asyncio.sleep(30)  # listen for 30 s
        sub_task.cancel()

        # Logs subscription example (commented out)
        # async def on_log(ctx, log):
        #     print(f"Log: {log}")
        # log_task = asyncio.create_task(
        #     manager.subscribe_logs(on_log, address="0xYourContract")
        # )

        manager.print_stats()


if __name__ == "__main__":
    asyncio.run(main())
