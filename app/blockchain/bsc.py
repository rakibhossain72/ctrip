from blockchain.base import BlockchainBase

class BSCBlockchain(BlockchainBase):
    def __init__(self, provider_url: str, **kwargs):
        # BSC Mainnet chain ID is 56
        super().__init__(provider_url, chain_id=56, use_poa=True, **kwargs)
