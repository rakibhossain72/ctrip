import asyncio
import logging
from datetime import datetime
import dramatiq
from sqlalchemy import select, update
from blockchain.w3 import get_w3, _w3_cache
from db.async_session import AsyncSessionLocal as async_session
from db.models.payment import Payment
from db.models.chain import ChainState
from core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIRMATIONS_REQUIRED = 1
BLOCK_BATCH_SIZE = 20

async def _scan_blocks():
    logger.info("=" * 60)
    logger.info("Starting block scan cycle")
    
    try:
        w3 = get_w3("anvil")
        logger.debug("Web3 instance obtained for chain: anvil")
        
        async with async_session() as session:
            logger.debug("Database session created")
            
            # Lock chain state row
            logger.debug("Acquiring lock on ChainState for chain: anvil")
            state = await session.execute(
                select(ChainState)
                .where(ChainState.chain == "anvil")
                .with_for_update()
            )
            state = state.scalar_one()
            logger.info(f"Current chain state - Last scanned block: {state.last_scanned_block}")
            
            latest_block = await w3.eth.block_number
            logger.info(f"Latest block on chain: {latest_block}")
            
            from_block = state.last_scanned_block + 1
            to_block = min(from_block + BLOCK_BATCH_SIZE, latest_block)
            
            if from_block > to_block:
                logger.info(f"No new blocks to scan (from_block: {from_block} > to_block: {to_block})")
                return
            
            logger.info(f"Scanning blocks {from_block} to {to_block} ({to_block - from_block + 1} blocks)")
            
            # Get pending payments
            payments = await session.execute(
                select(Payment)
                .where(Payment.status == "pending")
            )
            payment_list = list(payments.scalars())
            logger.info(f"Found {len(payment_list)} pending payments to monitor")
            
            payment_map = {
                p.address.lower(): p
                for p in payment_list
            }
            
            if payment_map:
                logger.debug(f"Monitoring addresses: {list(payment_map.keys())}")
            
            total_txs_scanned = 0
            payments_detected = 0
            
            for block_number in range(from_block, to_block + 1):
                logger.debug(f"Processing block {block_number}...")
                block = await w3.eth.get_block(block_number, full_transactions=True)
                
                tx_count = len(block.transactions)
                total_txs_scanned += tx_count
                logger.debug(f"Block {block_number} contains {tx_count} transactions")
                
                for tx in block.transactions:
                    if not tx.to:
                        continue
                    
                    addr = tx.to.lower()
                    if addr not in payment_map:
                        continue
                    
                    payment = payment_map[addr]
                    
                    logger.info(f"Found transaction to monitored address {addr}")
                    logger.info(f"  TX hash: {tx.hash.hex()}")
                    logger.info(f"  TX value: {tx.value} wei")
                    logger.info(f"  Expected: {payment.amount} wei")
                    logger.info(f"  Payment ID: {payment.id}")
                    
                    if tx.value < payment.amount:
                        logger.warning(f"  ❌ Insufficient amount - ignoring (received: {tx.value}, expected: {payment.amount_wei})")
                        continue
                    
                    # Mark as detected
                    logger.info(f"  ✅ Payment detected! Marking as DETECTED")
                    await session.execute(
                        update(Payment)
                        .where(Payment.id == payment.id)
                        .values(
                            status="detected",
                        )
                    )
                    payments_detected += 1
                    logger.info(f"  Payment {payment.id} updated to DETECTED status")
            
            # Advance chain state
            logger.info(f"Advancing chain state from block {state.last_scanned_block} to {to_block}")
            state.last_scanned_block = to_block
            await session.commit()
            
            logger.info(f"Scan complete - Scanned {total_txs_scanned} transactions across {to_block - from_block + 1} blocks")
            logger.info(f"Payments detected in this cycle: {payments_detected}")
            
    except Exception as e:
        logger.error(f"Error during block scan: {e}", exc_info=True)
        raise


async def _confirm_payments():
    logger.info("-" * 60)
    logger.info("Starting payment confirmation cycle")
    
    try:
        w3 = get_w3("anvil")
        latest_block = await w3.eth.block_number
        logger.info(f"Current block height: {latest_block}")
        
        async with async_session() as session:
            payments = await session.execute(
                select(Payment)
                .where(Payment.status == "detected")
            )
            
            detected_payments = list(payments.scalars())
            logger.info(f"Found {len(detected_payments)} payments in DETECTED status")
            
            confirmed_count = 0
            
            for payment in detected_payments:
                confirmations = latest_block - payment.detected_in_block + 1
                logger.info(f"Payment {payment.id}:")
                logger.info(f"  Current confirmations: {confirmations}/{CONFIRMATIONS_REQUIRED}")
                
                if confirmations >= CONFIRMATIONS_REQUIRED:
                    logger.info(f"  ✅ Payment has enough confirmations - marking as CONFIRMED")
                    await session.execute(
                        update(Payment)
                        .where(Payment.id == payment.id)
                        .values(
                            status="confirmed",
                            confirmations=confirmations,
                        )
                    )
                    confirmed_count += 1
                else:
                    remaining = CONFIRMATIONS_REQUIRED - confirmations
                    logger.info(f"  ⏳ Waiting for {remaining} more confirmation(s)")
            
            if confirmed_count > 0:
                await session.commit()
                logger.info(f"Confirmed {confirmed_count} payment(s) in this cycle")
            else:
                logger.info("No payments ready for confirmation")
                
    except Exception as e:
        logger.error(f"Error during payment confirmation: {e}", exc_info=True)
        raise


_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)

@dramatiq.actor(time_limit=10_000, max_retries=0)
def listen_for_payments():
    try:
        logger.info("🔊 Dramatiq actor: listen_for_payments triggered")
        _loop.run_until_complete(_scan_blocks())
        _loop.run_until_complete(_confirm_payments())
        logger.info("✅ Cycle complete - scheduling next run in 5 seconds")
    except Exception as e:
        logger.error(f"❌ Error in listener: {e}", exc_info=True)
    finally:
        listen_for_payments.send_with_options(delay=5000)


async def shutdown():
    logger.info("Shutting down - closing Web3 connections...")
    for chain_name, w3 in _w3_cache.items():
        logger.debug(f"Closing connection for chain: {chain_name}")
        provider = w3.provider
        if hasattr(provider, "session"):
            await provider.session.close()
            logger.debug(f"Session closed for {chain_name}")
    logger.info("All Web3 connections closed")


# Run with: python -m workers.long_listener (not via dramatiq workers)
async def main():
    logger.info("=" * 60)
    logger.info("🚀 Starting long listener service")
    logger.info(f"Configuration:")
    logger.info(f"  - Confirmations required: {CONFIRMATIONS_REQUIRED}")
    logger.info(f"  - Block batch size: {BLOCK_BATCH_SIZE}")
    logger.info(f"  - Poll interval: 5 seconds")
    logger.info("=" * 60)
    
    cycle_count = 0
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"\n{'=' * 60}")
            logger.info(f"CYCLE #{cycle_count} - {datetime.now().isoformat()}")
            logger.info(f"{'=' * 60}")
            
            await _scan_blocks()
            await _confirm_payments()
            
            logger.info(f"Cycle #{cycle_count} complete - sleeping for 5 seconds...")
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("\n⚠️  Keyboard interrupt received - shutting down gracefully...")
    except Exception as e:
        logger.error(f"❌ Fatal error in long listener: {e}", exc_info=True)
    finally:
        await shutdown()
        logger.info("👋 Long listener service stopped")


if __name__ == "__main__":
    asyncio.run(main())