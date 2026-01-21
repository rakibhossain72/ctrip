from eth_account import Account
from eth_account.hdaccount import generate_mnemonic, seed_from_mnemonic, key_from_seed


class HDWalletManager:
    """
    HD Wallet manager for Ethereum addresses using BIP-44 derivation.
    Path format: m/44'/60'/0'/0/{index}
    """

    def __init__(self, mnemonic_phrase=None):
        """
        Initialize HD Wallet with mnemonic phrase.

        Args:
            mnemonic_phrase: 12/24 word mnemonic. If None, generates new one.
        """
        if mnemonic_phrase is None:
            # Generate new mnemonic
            self.mnemonic = generate_mnemonic(num_words=12, lang="english")  # 12 words
        else:
            self.mnemonic = mnemonic_phrase

        # Derive seed from mnemonic
        self.seed = seed_from_mnemonic(self.mnemonic, passphrase="")

    def get_address(self, index):
        """
        Derive address at specific index using BIP-44 path.

        Args:
            index: Payment address index (0, 1, 2, ...)

        Returns:
            dict: {'address': checksummed_address, 'path': derivation_path}
        """
        # BIP-44 path for Ethereum: m/44'/60'/0'/0/{index}
        path = f"m/44'/60'/0'/0/{index}"

        # Derive private key from seed and path
        private_key = key_from_seed(self.seed, path)

        # Create account from private key
        account = Account.from_key(private_key)

        return {"address": account.address, "path": path, "index": index}

    def get_multiple_addresses(self, count, start_index=0):
        """
        Generate multiple addresses sequentially.

        Args:
            count: Number of addresses to generate
            start_index: Starting index (default 0)

        Returns:
            list: List of address dicts
        """
        addresses = []
        for i in range(start_index, start_index + count):
            addresses.append(self.get_address(i))
        return addresses

    def get_mnemonic(self):
        """Return the mnemonic phrase (KEEP THIS SECRET!)"""
        return self.mnemonic


# Example usage
if __name__ == "__main__":
    # Initialize wallet (in production, load existing mnemonic securely)
    wallet = HDWalletManager(
        "test test test test test test test test test test test junk"
    )
    print(f"\n{wallet.get_mnemonic()}\n")

    # Generate first 5 payment addresses
    addresses = wallet.get_multiple_addresses(5)

    for addr in addresses:
        print(f"\nIndex {addr['index']}:")
        print(f"  Path:    {addr['path']}")
        print(f"  Address: {addr['address']}")

    # Example: Get address for specific payment ID
    print("\nExample: Generate address for payment #42:")
    payment_42 = wallet.get_address(42)
    print(f"Address: {payment_42['address']}")
    print(f"Path: {payment_42['path']}")
