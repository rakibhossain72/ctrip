from web3 import Web3
from web3.middleware import BufferedGasEstimateMiddleware, ExtraDataToPOAMiddleware
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor


class BlockchainBase:
    def __init__(
        self, provider_url: str, request_timeout: int = 10, use_poa: bool = False
    ):
        """
        Initialize blockchain connection with optimizations.

        Args:
            provider_url: RPC endpoint URL
            request_timeout: Request timeout in seconds
            use_poa: Enable PoA middleware (for BSC, Polygon, etc.)
        """
        # Use persistent HTTP session for connection pooling
        from web3.providers import HTTPProvider
        from requests.adapters import HTTPAdapter
        from requests.sessions import Session

        session = Session()
        adapter = HTTPAdapter(
            pool_connections=20, pool_maxsize=20, max_retries=3, pool_block=False
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        provider = HTTPProvider(
            provider_url, request_kwargs={"timeout": request_timeout}, session=session
        )

        self.web3 = Web3(provider)

        # Add PoA middleware if needed (BSC, Polygon, etc.)
        self.web3.middleware_onion.inject(BufferedGasEstimateMiddleware, layer=0)
        if use_poa:
            self.web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


        # Cache for gas price (expires based on your needs)
        self._gas_price_cache = None
        self._gas_price_timestamp = 0
        self._gas_cache_duration = 10  # seconds

        # Thread pool for parallel operations
        self._executor = ThreadPoolExecutor(max_workers=10)

    def is_connected(self) -> bool:
        """Check blockchain connection."""
        return self.web3.is_connected()

    def get_balance(self, address: str) -> float:
        """Get balance in ETH for an address."""
        checksum_address = Web3.to_checksum_address(address)
        balance_wei = self.web3.eth.get_balance(checksum_address)
        return self.web3.from_wei(balance_wei, "ether")

    def get_gas_price(self, use_cache: bool = True) -> float:
        """
        Get current gas price with optional caching.

        Args:
            use_cache: Whether to use cached gas price
        """
        import time

        if use_cache:
            current_time = time.time()
            if (
                self._gas_price_cache is not None
                and current_time - self._gas_price_timestamp < self._gas_cache_duration
            ):
                return self._gas_price_cache

        gas_price_wei = self.web3.eth.gas_price
        gas_price_gwei = self.web3.from_wei(gas_price_wei, "gwei")

        if use_cache:
            self._gas_price_cache = gas_price_gwei
            self._gas_price_timestamp = time.time()

        return gas_price_gwei

    def estimate_gas(
        self, from_address: str, to_address: str, amount_eth: float
    ) -> int:
        """Estimate gas for a transaction."""
        tx = {
            "from": Web3.to_checksum_address(from_address),
            "to": Web3.to_checksum_address(to_address),
            "value": self.web3.to_wei(amount_eth, "ether"),
        }
        return self.web3.eth.estimate_gas(tx)

    def build_transaction(
        self,
        from_address: str,
        to_address: str,
        amount_eth: float,
        gas_limit: Optional[int] = None,
        gas_price_gwei: Optional[float] = None,
        nonce: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build transaction dict (separate from signing for better performance).

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount_eth: Amount in ETH
            gas_limit: Optional pre-calculated gas limit
            gas_price_gwei: Optional gas price in gwei
            nonce: Optional pre-fetched nonce
        """
        from_checksum = Web3.to_checksum_address(from_address)
        to_checksum = Web3.to_checksum_address(to_address)

        # Use provided values or fetch them
        if nonce is None:
            nonce = self.web3.eth.get_transaction_count(from_checksum, "pending")

        if gas_price_gwei is None:
            gas_price_gwei = self.get_gas_price()

        if gas_limit is None:
            gas_limit = self.estimate_gas(from_address, to_address, amount_eth)

        # Add 10% buffer to gas limit for safety
        gas_limit = int(gas_limit * 1.1)

        tx = {
            "nonce": nonce,
            "to": to_checksum,
            "value": self.web3.to_wei(amount_eth, "ether"),
            "gas": gas_limit,
            "gasPrice": self.web3.to_wei(gas_price_gwei, "gwei"),
            "chainId": self.web3.eth.chain_id,
        }

        return tx

    def send_transaction(
        self,
        from_address: str,
        to_address: str,
        amount_eth: float,
        private_key: str,
        gas_limit: Optional[int] = None,
        gas_price_gwei: Optional[float] = None,
        wait_for_receipt: bool = False,
    ) -> str:
        """
        Send a transaction.

        Args:
            from_address: Sender address
            to_address: Recipient address
            amount_eth: Amount in ETH
            private_key: Private key for signing
            gas_limit: Optional pre-calculated gas limit
            gas_price_gwei: Optional gas price in gwei
            wait_for_receipt: Whether to wait for transaction receipt
        """
        tx = self.build_transaction(
            from_address, to_address, amount_eth, gas_limit, gas_price_gwei
        )

        signed_tx = self.web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = self.web3.to_hex(tx_hash)

        if wait_for_receipt:
            receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
            return tx_hash_hex, receipt

        return tx_hash_hex

    def batch_get_balances(self, addresses: list) -> Dict[str, float]:
        """
        Get balances for multiple addresses in parallel.

        Args:
            addresses: List of addresses to check
        """

        def get_bal(addr):
            return addr, self.get_balance(addr)

        results = self._executor.map(get_bal, addresses)
        return dict(results)

    def get_transaction_receipt(self, tx_hash: str, timeout: int = 120):
        """
        Get transaction receipt.

        Args:
            tx_hash: Transaction hash
            timeout: Timeout in seconds
        """
        return self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=timeout)

    def get_latest_block_number(self) -> int:
        """Get the latest block number."""
        return self.web3.eth.block_number
    
    def is_valid_address(self, address: str) -> bool:
        """Check if an address is valid."""
        return self.web3.is_address(address)

    def get_async_provider(self):
        """Get an async provider using the current connection settings."""
        from web3.providers.rpc import AsyncHTTPProvider
        
        return AsyncHTTPProvider(self.web3.provider.endpoint_uri)

    def __del__(self):
        """Cleanup thread pool on deletion."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=False)
