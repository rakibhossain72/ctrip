# Configuration

cTrip is highly customizable, and separates its settings into environment variables for runtime parameters/secrets and structured YAML for network topologies.

---

## Environment Variables (`.env`)

Environment configurations are managed securely using `pydantic-settings`. At runtime, variables are loaded from the system environment or a `.env` file at the root.

Here is a full reference guide to the supported variables:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ENV` | `string` | `development` | Core mode: `development`, `production`, or `testing` |
| `DATABASE_URL` | `string` | `postgresql://...` | Relational database connection string (Production) |
| `DATABASE_URL_DEV` | `string` | `sqlite:///./dev_database.db` | SQLite connection string (Development) |
| `REDIS_URL` | `string` | `redis://localhost:6379/0` | Connection string for worker queue & broker |
| `PRIVATE_KEY` | `string` | *None* | **[REQUIRED]** Ethereum Private Key for admin/sweeping |
| `WALLET_SECRET_A` | `string` | *None* | **[REQUIRED]** Component A for secure address generation |
| `WALLET_SECRET_B` | `string` | *None* | **[REQUIRED]** Component B for secure address generation |
| `MNEMONIC` | `string` | `test test ... junk` | Hierarchical Deterministic wallet recovery phrase |
| `WEBHOOK_URL` | `string` | *None* | Global target URL for payment notification events |
| `WEBHOOK_SECRET` | `string` | *None* | Signing secret to generate payload signature hashes |
| `SECRET_KEY` | `string` | `your-secret-key-...`| Secure cryptographical key used for sessions |
| `PAYMENT_EXPIRY_MINUTES` | `int` | `30` | Minutes before an unpaid payment expires |

### Example `.env` File
```ini
ENV=development
DATABASE_URL_DEV=sqlite:///./dev_database.db
REDIS_URL=redis://localhost:6379/0
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
WALLET_SECRET_A=secret_a_component_here
WALLET_SECRET_B=secret_b_component_here
MNEMONIC="test test test test test test test test test test test junk"
WEBHOOK_URL=https://merchant.example.com/api/v1/payments/webhook
WEBHOOK_SECRET=super-secret-signature-key
```

---

## Blockchain Networks Configuration (`chains.yaml`)

Supported networks and their corresponding tokens are defined cleanly in `chains.yaml` inside the root repository.

### Structure & Parameters
The file contains an array of chain items. Each chain item supports the following fields:

*   **`name`**: Lowercase matching string for the network identifier (e.g., `bsc`, `ethereum`, `anvil`).
*   **`rpc_url`**: RPC node server endpoint. **Must use a WebSocket (`ws://` or `wss://`) endpoint to support real-time scanning by `chain-sniper`.**
*   **`confirmations_required`**: Number of block confirmations before a payment is marked as `CONFIRMED`.
*   **`tokens`**: List of supported ERC20 contracts on this network.
    *   `symbol`: Uppercase identifier (e.g., `USDT`, `USDC`).
    *   `address`: Contract address on the blockchain. Omit or leave null for native network currencies (e.g., BNB, ETH).
    *   `decimals`: Token precision.

### Example `chains.yaml`
```yaml
- name: anvil
  rpc_url: ws://localhost:8545
  confirmations_required: 1
  tokens:
    - symbol: ETH
      address: null
      decimals: 18

- name: bsc
  rpc_url: wss://bsc-ws-node.example.com
  confirmations_required: 3
  tokens:
    - symbol: USDT
      address: "0x55d398326f99059ff775485246999027b3197955"
      decimals: 18

- name: ethereum
  rpc_url: wss://mainnet.infura.io/ws/v3/YOUR_API_KEY
  confirmations_required: 12
  tokens:
    - symbol: USDT
      address: "0xdac17f958d2ee523a2206206994597c13d831ec7"
      decimals: 6
```

---

## Secure Address Generation Mechanics

To ensure user checkout security, cTrip uses **Hierarchical Deterministic (HD) wallets** implementing **BIP-44 standards** to generate unique deposit addresses sequentially.

```
Mnemonic Seed (MNEMONIC)
   ↓ (Derivation Path)
m/44'/60'/0'/0/index
   ↓
Uniquely derived address index:
   - Index 0  → Address A (Customer Order 1)
   - Index 1  → Address B (Customer Order 2)
   - Index 2  → Address C (Customer Order 3)
```

### Derivation Path Details
For EVM support, cTrip uses the standard Ethereum path:
$$\text{Path: } m/44'/60'/0'/0/index$$

### Security Best Practices
1.  **Do Not Reuse Seeds**: Never reuse your production mnemonic seed across testing/staging environments.
2.  **Zero-Leak Policy**: Mnemonic strings and private keys are never written to standard output logs, database collections, or response bodies.
3.  **Environment Variable Isolation**: Always configure `MNEMONIC`, `PRIVATE_KEY`, and `WALLET_SECRET` credentials using secure runtime secrets or production KMS systems.
