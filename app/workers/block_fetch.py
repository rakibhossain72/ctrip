import asyncio
import logging
from typing import Optional, List, Dict, Set
from datetime import datetime
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.types import BlockData, TxData, TxReceipt, LogReceipt
from eth_abi.abi import decode
from eth_typing import ChecksumAddress
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('payment_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
MONITORED_ADDRESSES = [
    '0x55C3158F657a85B30b4c93E4756fbc942a15313c',
]

MONITORED_TOKENS = {
    # 'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
    # 'USDC': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48',
}

# Transfer event signature: Transfer(address,address,uint256)
TRANSFER_TOPIC = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

# RPC endpoints (fallback chain)
RPC_ENDPOINTS = [
    # 'https://ethereum-rpc.publicnode.com',
    # 'https://eth.llamarpc.com',
    # 'https://rpc.ankr.com/eth',
    # 'https://cloudflare-eth.com',
    'http://127.0.0.1:8545'
]

# Retry configuration
MAX_RETRIES = 5
RETRY_WAIT_MIN = 1  # seconds
RETRY_WAIT_MAX = 60  # seconds
BLOCK_POLL_INTERVAL = 12  # seconds (Ethereum block time)
MAX_CONCURRENT_REQUESTS = 10  # Limit concurrent RPC requests


class PaymentMonitor:
    """Robust Ethereum payment monitoring system with HTTPS polling"""
    
    def __init__(self):
        self.w3: Optional[AsyncWeb3] = None
        self.current_rpc_index = 0
        self.processed_blocks: Set[int] = set()
        self.last_processed_block: Optional[int] = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        
        # Normalize addresses to checksum format
        self.monitored_addresses = [
            AsyncWeb3.to_checksum_address(addr.lower()) 
            for addr in MONITORED_ADDRESSES
        ]
        self.monitored_tokens = {
            symbol: AsyncWeb3.to_checksum_address(addr.lower())
            for symbol, addr in MONITORED_TOKENS.items()
        }
        
    async def connect_with_fallback(self) -> bool:
        """Try connecting to RPC endpoints with fallback"""
        for i, endpoint in enumerate(RPC_ENDPOINTS):
            try:
                logger.info(f"Attempting to connect to {endpoint}")
                provider = AsyncHTTPProvider(
                    endpoint,
                    request_kwargs={
                        'timeout': 30,
                        'headers': {'Content-Type': 'application/json'}
                    }
                )
                w3 = AsyncWeb3(provider)
                
                # Test connection
                if await w3.is_connected():
                    chain_id = await w3.eth.chain_id
                    logger.info(f"Connected to Ethereum (Chain ID: {chain_id}) via {endpoint}")
                    self.w3 = w3
                    self.current_rpc_index = i
                    return True
                    
            except Exception as e:
                logger.warning(f"Failed to connect to {endpoint}: {str(e)}")
                continue
                
        logger.error("Failed to connect to any RPC endpoint")
        return False
        
    async def switch_rpc_endpoint(self):
        """Switch to next RPC endpoint in fallback chain"""
        self.current_rpc_index = (self.current_rpc_index + 1) % len(RPC_ENDPOINTS)
        logger.info(f"Switching to RPC endpoint: {RPC_ENDPOINTS[self.current_rpc_index]}")
        await self.connect_with_fallback()
        
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get_block_with_retry(self, block_number: int) -> Optional[BlockData]:
        """Get block data with retry logic"""
        async with self.semaphore:
            try:
                block = await self.w3.eth.get_block(block_number, full_transactions=True)
                return block
            except Exception as e:
                logger.error(f"Error fetching block {block_number}: {str(e)}")
                # Try switching endpoint on persistent errors
                await self.switch_rpc_endpoint()
                raise
                
    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, Exception)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get_receipt_with_retry(self, tx_hash: bytes) -> Optional[TxReceipt]:
        """Get transaction receipt with retry logic"""
        async with self.semaphore:
            try:
                receipt = await self.w3.eth.get_transaction_receipt(tx_hash)
                return receipt
            except Exception as e:
                logger.error(f"Error fetching receipt for {tx_hash.hex()}: {str(e)}")
                await self.switch_rpc_endpoint()
                raise
                
    async def process_payment(
        self,
        tx: TxData,
        receipt: TxReceipt,
        is_eth: bool,
        token_symbol: str = None,
        amount: int = 0
    ):
        """Process detected payment (placeholder for your business logic)"""
        try:
            if is_eth:
                eth_amount = self.w3.from_wei(tx['value'], 'ether')
                logger.info(
                    f"✅ ETH Payment Detected\n"
                    f"   From: {tx['from']}\n"
                    f"   To: {tx['to']}\n"
                    f"   Amount: {eth_amount} ETH\n"
                    f"   TxHash: {tx['hash'].hex()}\n"
                    f"   Block: {tx['blockNumber']}\n"
                    f"   Status: {'Success' if receipt['status'] == 1 else 'Failed'}"
                )
            else:
                # Convert amount based on token decimals (assuming 6 for USDC/USDT)
                decimals = 6 if token_symbol in ['USDC', 'USDT'] else 18
                readable_amount = amount / (10 ** decimals)
                
                logger.info(
                    f"✅ {token_symbol} Payment Detected\n"
                    f"   To: {tx['to']}\n"
                    f"   Amount: {readable_amount} {token_symbol}\n"
                    f"   TxHash: {tx['hash'].hex()}\n"
                    f"   Block: {tx['blockNumber']}\n"
                    f"   Status: {'Success' if receipt['status'] == 1 else 'Failed'}"
                )
                
            # TODO: Add your payment processing logic here
            # Examples:
            # - Store in database
            # - Send webhook notification
            # - Update order status
            # - Trigger business logic
            
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}", exc_info=True)
            
    def decode_transfer_log(self, log: LogReceipt) -> Optional[tuple]:
        """Safely decode ERC20 Transfer event log"""
        try:
            # Validate log structure
            if len(log['topics']) < 3:
                return None
                
            # Extract 'to' address from topics[2]
            to_address_padded = log['topics'][2].hex()
            to_address = f"0x{to_address_padded[-40:]}"
            to_address_checksum = self.w3.to_checksum_address(to_address)
            
            # Decode amount from data
            if not log['data'] or log['data'] == '0x':
                return None
                
            data_bytes = bytes.fromhex(log['data'][2:])
            amount = int.from_bytes(decode(['uint256'], data_bytes)[0], 'big')
            
            return (to_address_checksum, amount)
            
        except Exception as e:
            logger.warning(f"Failed to decode transfer log: {str(e)}")
            return None
            
    async def process_transaction(self, tx: TxData):
        """Process a single transaction for payments"""
        try:
            # Check for direct ETH transfer
            if tx['to'] and tx['to'] in self.monitored_addresses and tx['value'] > 0:
                receipt = await self.get_receipt_with_retry(tx['hash'])
                if receipt and receipt['status'] == 1:  # Only successful transactions
                    await self.process_payment(tx, receipt, is_eth=True)
                    
            # Check for ERC20 token transfers
            receipt = await self.get_receipt_with_retry(tx['hash'])
            
            if not receipt or receipt['status'] != 1:
                return  # Skip failed transactions
                
            for log in receipt.get('logs', []):
                # Check if this is a Transfer event from monitored token
                if (log['address'] in self.monitored_tokens.values() and 
                    log['topics'] and 
                    log['topics'][0].hex() == TRANSFER_TOPIC):
                    
                    decoded = self.decode_transfer_log(log)
                    if not decoded:
                        continue
                        
                    to_address, amount = decoded
                    
                    # Check if transfer is to monitored address
                    if to_address in self.monitored_addresses:
                        token_symbol = next(
                            (sym for sym, addr in self.monitored_tokens.items() 
                             if addr == log['address']),
                            'Unknown'
                        )
                        await self.process_payment(
                            tx, receipt, 
                            is_eth=False, 
                            token_symbol=token_symbol, 
                            amount=amount
                        )
                        
        except Exception as e:
            logger.error(f"Error processing transaction {tx['hash'].hex()}: {str(e)}")
            
    async def process_block(self, block_number: int):
        """Process a single block"""
        # Skip if already processed
        if block_number in self.processed_blocks:
            return
            
        try:
            block = await self.get_block_with_retry(block_number)
            
            if not block:
                logger.warning(f"Block {block_number} returned None")
                return
                
            tx_count = len(block.get('transactions', []))
            logger.info(f"Processing block {block_number} with {tx_count} transactions")
            
            # Process transactions concurrently with semaphore limiting
            tasks = [
                self.process_transaction(tx) 
                for tx in block.get('transactions', [])
            ]
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                
            # Mark as processed
            self.processed_blocks.add(block_number)
            self.last_processed_block = block_number
            
            # Cleanup old processed blocks (keep last 1000)
            if len(self.processed_blocks) > 1000:
                min_block = min(self.processed_blocks)
                self.processed_blocks.discard(min_block)
                
        except Exception as e:
            logger.error(f"Error processing block {block_number}: {str(e)}")
            
    async def catch_up_missed_blocks(self, from_block: int, to_block: int):
        """Process missed blocks during downtime"""
        logger.info(f"Catching up blocks from {from_block} to {to_block}")
        
        for block_num in range(from_block, to_block + 1):
            try:
                await self.process_block(block_num)
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"Error catching up block {block_num}: {str(e)}")
                
    async def monitor_loop(self):
        """Main monitoring loop with HTTPS polling"""
        logger.info("Starting payment monitoring service...")
        
        # Get starting block
        current_block = await self.w3.eth.block_number
        self.last_processed_block = current_block
        logger.info(f"Starting from block {current_block}")
        
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        while True:
            try:
                # Get latest block
                latest_block = await self.w3.eth.block_number
                
                # Check for missed blocks
                if self.last_processed_block and latest_block > self.last_processed_block + 1:
                    missed_blocks = latest_block - self.last_processed_block - 1
                    logger.warning(f"Detected {missed_blocks} missed blocks, catching up...")
                    await self.catch_up_missed_blocks(
                        self.last_processed_block + 1,
                        latest_block - 1
                    )
                
                # Process latest block
                await self.process_block(latest_block)
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # Wait for next block
                await asyncio.sleep(BLOCK_POLL_INTERVAL)
                
            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Error in monitoring loop (consecutive errors: {consecutive_errors}): {str(e)}",
                    exc_info=True
                )
                
                # If too many consecutive errors, try reconnecting
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Too many consecutive errors, attempting to reconnect...")
                    await self.connect_with_fallback()
                    consecutive_errors = 0
                    
                # Exponential backoff
                backoff = min(2 ** consecutive_errors, 60)
                await asyncio.sleep(backoff)
                
    async def run(self):
        """Start the payment monitor"""
        try:
            # Initial connection
            if not await self.connect_with_fallback():
                logger.error("Could not establish initial connection")
                return
                
            # Start monitoring
            await self.monitor_loop()
            
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
        finally:
            logger.info("Payment monitor shutdown complete")


async def main():
    """Entry point"""
    monitor = PaymentMonitor()
    await monitor.run()


if __name__ == "__main__":
    asyncio.run(main())