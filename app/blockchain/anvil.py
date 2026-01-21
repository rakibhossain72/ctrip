from blockchain.base import BlockchainBase
from typing import Optional, List, Dict, Any
import time


class AnvilBlockchain(BlockchainBase):
    def __init__(self, provider_url: str = "http://localhost:8545"):
        """
        Initialize Anvil blockchain connection.

        Args:
            provider_url: RPC endpoint URL for Anvil (default: localhost:8545)
        """
        super().__init__(provider_url=provider_url, request_timeout=5, use_poa=False)

        # Anvil-specific optimizations
        self._gas_cache_duration = 30  # Anvil gas price is more stable

    def get_gas_price(self, use_cache: bool = True) -> float:
        """
        Get current gas price with caching optimized for Anvil.

        Args:
            use_cache: Whether to use cached gas price
        """
        current_time = time.time()
        if (
            use_cache
            and self._gas_price_cache is not None
            and (current_time - self._gas_price_timestamp) < self._gas_cache_duration
        ):
            return self._gas_price_cache

        # Fetch fresh gas price
        gas_price_wei = self.web3.eth.gas_price
        gas_price_gwei = self.web3.from_wei(gas_price_wei, "gwei")

        # Update cache
        if use_cache:
            self._gas_price_cache = gas_price_gwei
            self._gas_price_timestamp = current_time

        return gas_price_gwei

    def mine_blocks(self, num_blocks: int = 1) -> List[str]:
        """
        Mine blocks in Anvil for testing purposes.

        Args:
            num_blocks: Number of blocks to mine

        Returns:
            List of block hashes
        """
        block_hashes = []
        for _ in range(num_blocks):
            result = self.web3.provider.make_request("evm_mine", [])
            block_hashes.append(result.get("result"))
        return block_hashes

    def set_next_block_timestamp(self, timestamp: int) -> bool:
        """
        Set the timestamp for the next block in Anvil.

        Args:
            timestamp: Unix timestamp

        Returns:
            Success status
        """
        result = self.web3.provider.make_request(
            "evm_setNextBlockTimestamp", [timestamp]
        )
        return result.get("result") is not None

    def increase_time(self, seconds: int) -> int:
        """
        Increase time in Anvil by specified seconds.

        Args:
            seconds: Number of seconds to increase

        Returns:
            New timestamp
        """
        result = self.web3.provider.make_request("evm_increaseTime", [seconds])
        self.mine_blocks(1)  # Mine a block to apply the time change
        return result.get("result", 0)

    def snapshot(self) -> int:
        """
        Create a snapshot of the current blockchain state.

        Returns:
            Snapshot ID
        """
        result = self.web3.provider.make_request("evm_snapshot", [])
        return result.get("result", 0)

    def revert(self, snapshot_id: int) -> bool:
        """
        Revert to a previous snapshot.

        Args:
            snapshot_id: ID of the snapshot to revert to

        Returns:
            Success status
        """
        result = self.web3.provider.make_request("evm_revert", [snapshot_id])
        return result.get("result", False)

    def set_balance(self, address: str, balance_eth: float) -> bool:
        """
        Set the ETH balance of an address in Anvil.

        Args:
            address: Address to set balance for
            balance_eth: Balance in ETH

        Returns:
            Success status
        """
        address_checksum = self.web3.to_checksum_address(address)
        balance_wei = self.web3.to_wei(balance_eth, "ether")
        balance_hex = hex(balance_wei)

        result = self.web3.provider.make_request(
            "anvil_setBalance", [address_checksum, balance_hex]
        )
        return result.get("result") is not None

    def impersonate_account(self, address: str) -> bool:
        """
        Start impersonating an account in Anvil.

        Args:
            address: Address to impersonate

        Returns:
            Success status
        """
        address_checksum = self.web3.to_checksum_address(address)
        result = self.web3.provider.make_request(
            "anvil_impersonateAccount", [address_checksum]
        )
        return result.get("result") is not None

    def stop_impersonating_account(self, address: str) -> bool:
        """
        Stop impersonating an account in Anvil.

        Args:
            address: Address to stop impersonating

        Returns:
            Success status
        """
        address_checksum = self.web3.to_checksum_address(address)
        result = self.web3.provider.make_request(
            "anvil_stopImpersonatingAccount", [address_checksum]
        )
        return result.get("result") is not None

    def reset(
        self, forking_url: Optional[str] = None, block_number: Optional[int] = None
    ) -> bool:
        """
        Reset Anvil to a fresh state or fork from a network.

        Args:
            forking_url: Optional URL to fork from
            block_number: Optional block number to fork from

        Returns:
            Success status
        """
        params = {}
        if forking_url:
            params["forking"] = {"jsonRpcUrl": forking_url}
            if block_number:
                params["forking"]["blockNumber"] = block_number

        result = self.web3.provider.make_request(
            "anvil_reset", [params] if params else []
        )
        return result.get("result") is not None

    def auto_mine(self, enabled: bool = True) -> bool:
        """
        Enable or disable auto-mining in Anvil.

        Args:
            enabled: Whether to enable auto-mining

        Returns:
            Success status
        """
        result = self.web3.provider.make_request("evm_setAutomine", [enabled])
        return result.get("result") is not None

    def set_interval_mining(self, interval_seconds: int) -> bool:
        """
        Set interval mining in Anvil (mine a block every N seconds).

        Args:
            interval_seconds: Seconds between blocks (0 to disable)

        Returns:
            Success status
        """
        result = self.web3.provider.make_request(
            "evm_setIntervalMining", [interval_seconds]
        )
        return result.get("result") is not None

    def get_accounts(self) -> List[str]:
        """
        Get all accounts available in Anvil.

        Returns:
            List of account addresses
        """
        return self.web3.eth.accounts

    def send_transaction_with_impersonation(
        self,
        from_address: str,
        to_address: str,
        amount_eth: float,
        gas_limit: Optional[int] = None,
        wait_for_receipt: bool = True,
    ) -> str:
        """
        Send transaction by impersonating an account (useful for testing).

        Args:
            from_address: Address to send from (will be impersonated)
            to_address: Recipient address
            amount_eth: Amount in ETH
            gas_limit: Optional gas limit
            wait_for_receipt: Whether to wait for receipt

        Returns:
            Transaction hash
        """
        # Impersonate the account
        self.impersonate_account(from_address)

        try:
            # Build transaction without private key
            tx = self.build_transaction(
                from_address, to_address, amount_eth, gas_limit=gas_limit
            )

            # Send transaction (no signature needed when impersonating)
            tx_hash = self.web3.eth.send_transaction(tx)
            tx_hash_hex = self.web3.to_hex(tx_hash)

            if wait_for_receipt:
                receipt = self.web3.eth.wait_for_transaction_receipt(
                    tx_hash, timeout=30
                )
                return tx_hash_hex, receipt

            return tx_hash_hex
        finally:
            # Stop impersonating
            self.stop_impersonating_account(from_address)

    def fast_forward(self, seconds: int, mine: bool = True) -> Dict[str, Any]:
        """
        Fast forward time in Anvil and optionally mine a block.

        Args:
            seconds: Number of seconds to fast forward
            mine: Whether to mine a block after time increase

        Returns:
            Dictionary with new timestamp and block info
        """
        new_timestamp = self.increase_time(seconds)

        result = {"timestamp": new_timestamp, "seconds_increased": seconds}

        if mine:
            block_hashes = self.mine_blocks(1)
            latest_block = self.web3.eth.get_block("latest")
            result["block_number"] = latest_block["number"]
            result["block_hash"] = block_hashes[0] if block_hashes else None

        return result
