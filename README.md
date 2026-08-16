# cTrip Payment Gateway

A self-hosted, multi-chain cryptocurrency payment gateway built with FastAPI. Create on-chain payment requests, receive funds into unique deterministic deposit addresses, and track every payment through detection, confirmation, settlement, and notification across any number of EVM-compatible blockchains.

## Highlights

- **Multi-chain** — BSC, Ethereum, Sepolia, and any other EVM network, configured declaratively in `chains.yaml` with per-chain RPC failover.
- **Reliable detection** — cron-driven block scanner with Redis-backed cursors; supports native and ERC-20 payments. No polling code in your application.
- **Deterministic addresses** — HKDF-derived deposit addresses per order; private keys are recomputable, never stored.
- **Full lifecycle** — `pending → detected → confirmed → settled`, with expiry and confirmation tracking.
- **Fund sweeping** — confirmed balances are swept automatically to your main wallet.
- **Signed webhooks** — HMAC-SHA256 signed events with retries and exponential backoff.
- **Admin console & analytics** — server-rendered admin UI and REST analytics for volume, daily trends, and webhook health.

## Quick Start

```bash
git clone <your-repo-url> && cd ctrip
cp .env.example .env
docker-compose up --build
```

API is served at `http://localhost:8000` (interactive docs at `/docs`), admin console at `/admin`.

For local development without Docker:

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python migrate.py upgrade
uvicorn server:app --reload          # terminal 1
python run_worker.py                 # terminal 2
```

## Documentation

Full documentation is available at [ctrip-docs.readthedocs.io](https://ctrip-docs.readthedocs.io/).

| Topic | Page |
|------|------|
| Setup & prerequisites | [Getting Started](https://ctrip-docs.readthedocs.io/en/latest/) |
| System design & payment lifecycle | [Core Architecture](https://ctrip-docs.readthedocs.io/en/latest/architecture/) |
| Environment & `chains.yaml` | [Configuration](https://ctrip-docs.readthedocs.io/en/latest/configuration/) |
| REST endpoints & webhooks | [API Reference](https://ctrip-docs.readthedocs.io/en/latest/api-reference/) |
| Local Anvil, migrations, testing | [Development & Operations](https://ctrip-docs.readthedocs.io/en/latest/development/) |

## Project Structure

```
ctrip/
├── app/           # FastAPI application (api, blockchain, db, services, wallet, workers)
├── scanner/       # Block-scanning engine (orchestrator, jobs, matching)
├── alembic/       # Database migrations
├── example/       # End-to-end usage scripts
├── chains.yaml    # Blockchain configuration
├── migrate.py     # Migration helper
├── run_worker.py  # ARQ worker entrypoint
└── server.py      # FastAPI application entrypoint
```

## License

This project is licensed under the terms included in the [LICENSE.txt](LICENSE.txt) file.
