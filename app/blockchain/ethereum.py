from app.blockchain.base import BlockchainBase

class EthereumBlockchain(BlockchainBase):
    def __init__(self, provider_url: str, **kwargs):
        # Ethereum Mainnet chain ID is 1
        super().__init__(provider_url, chain_id=1, use_poa=False, **kwargs)
