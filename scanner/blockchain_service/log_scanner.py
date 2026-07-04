from __future__ import annotations

from typing import Iterable, Optional

from web3.types import LogReceipt

from .connection import ChainConnectionManager
from .retry import RetryPolicy
from .constants import ERC20_TRANSFER_TOPIC
from .utils import addresses_to_topics


class LogScanner:
    """Scans chain logs via eth_getLogs, with a dedicated helper for
    ERC20 Transfer events filtered by token / sender / receiver address.
    """

    def __init__(
        self, connections: ChainConnectionManager, retry_policy: RetryPolicy
    ) -> None:
        self.connections = connections
        self.retry_policy = retry_policy

    async def get_logs(
        self,
        chain_id: int,
        *,
        from_block: int,
        to_block: int,
        address: Optional[list[str]] = None,
        topics: Optional[list] = None,
    ) -> Optional[list[LogReceipt]]:
        """Generic log fetch. `address` may be a single contract or a list of
        contracts; `topics` follows the standard eth_getLogs topic format,
        where each position may be a single topic, a list of topics
        (OR'd together), or None (matches anything in that position).
        """
        w3 = self.connections.get(chain_id)
        if not w3:
            return None

        filter_params: dict = {
            "fromBlock": from_block,
            "toBlock": to_block,
        }
        if address:
            filter_params["address"] = address
        if topics:
            filter_params["topics"] = topics

        return await self.retry_policy.run(
            f"get_logs({self.connections.chain_name(chain_id)}, {from_block}-{to_block})",
            lambda: w3.eth.get_logs(filter_params),
        )

    async def get_erc20_transfer_logs(
        self,
        chain_id: int,
        *,
        from_block: int,
        to_block: int,
        token_addresses: Optional[Iterable[str]] = None,
        sender_addresses: Optional[Iterable[str]] = None,
        receiver_addresses: Optional[Iterable[str]] = None,
    ) -> Optional[list[LogReceipt]]:
        """
        Fetch ERC20 `Transfer(address indexed from, address indexed to, uint256 value)`
        logs for one or more chains' tokens, optionally filtered by:

          - token_addresses:    contract addresses to scan (maps to `address`)
          - sender_addresses:   `from` addresses            (maps to topic[1])
          - receiver_addresses: `to` addresses               (maps to topic[2])

        Each filter accepts multiple addresses (OR'd together within that
        position) and any of the three may be omitted to match all values
        for that slot. Examples:

            # All transfers of two tokens, any sender/receiver
            await scanner.get_erc20_transfer_logs(
                chain_id, from_block=1, to_block=100,
                token_addresses=["0xTokenA", "0xTokenB"],
            )

            # Transfers of one token FROM any of two addresses
            await scanner.get_erc20_transfer_logs(
                chain_id, from_block=1, to_block=100,
                token_addresses=["0xTokenA"],
                sender_addresses=["0xAlice", "0xBob"],
            )

            # Transfers TO a specific address, across all tokens
            await scanner.get_erc20_transfer_logs(
                chain_id, from_block=1, to_block=100,
                receiver_addresses=["0xRecipient"],
            )
        """
        from_topics = addresses_to_topics(sender_addresses)
        to_topics = addresses_to_topics(receiver_addresses)

        topics: list = [ERC20_TRANSFER_TOPIC]
        if from_topics is not None or to_topics is not None:
            topics.append(from_topics)  # None here means "any sender"
            if to_topics is not None:
                topics.append(to_topics)

        token_list = list(token_addresses) if token_addresses else None

        return await self.get_logs(
            chain_id,
            from_block=from_block,
            to_block=to_block,
            address=token_list,
            topics=topics,
        )
