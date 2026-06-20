"""
End-to-end payment simulation script.

Flow
----
1. Login with admin credentials  -> receive JWT access token
2. Create an API key             -> receive raw key (shown once)
3. Create a payment              -> receive payment address
4. Send a native ETH transaction -> fund the payment address
5. Poll payment status           -> wait for DETECTED / CONFIRMED

Usage
-----
  python example/create_payment.py

Options (override via env vars or command-line flags):
  BASE_URL          API base URL         (default: http://127.0.0.1:8000)
  RPC_URL           Anvil RPC URL        (default: http://127.0.0.1:8545)
  ADMIN_USERNAME    Admin username       (default: admin)
  ADMIN_PASSWORD    Admin password       (default: admin123)
  SENDER_KEY        Sender private key   (default: first Anvil test key)
  PAYMENT_AMOUNT    Amount in wei        (default: 100_000_000_000_000_000 = 0.1 ETH)
  PAYMENT_CHAIN     Chain name           (default: anvil)


# default — login as admin/admin123, create key, pay 0.1 ETH on anvil
python example/create_payment.py

# point at a remote server
python example/create_payment.py --base-url https://api.example.com --username admin --password s3cr3t

# ERC-20 payment
python example/create_payment.py --token 0xContractAddress --amount 1000000

# create the payment without sending a tx (useful for manual wallet testing)
python example/create_payment.py --no-tx

"""

import argparse
import json
import os
import sys
import time

import requests
import web3 as Web3Module
from web3 import Web3

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULTS = {
    "base_url":   os.getenv("BASE_URL",         "http://127.0.0.1:8000"),
    "rpc_url":    os.getenv("RPC_URL",           "http://127.0.0.1:8545"),
    "username":   os.getenv("ADMIN_USERNAME",    "admin"),
    "password":   os.getenv("ADMIN_PASSWORD",    "admin123"),
    "sender_key": os.getenv(
        "SENDER_KEY",
        # Default Anvil/Hardhat test account #0 — never use in production
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    ),
    "amount":     int(os.getenv("PAYMENT_AMOUNT", 100_000_000_000_000_000)),  # 0.1 ETH
    "chain":      os.getenv("PAYMENT_CHAIN",     "anvil"),
}

# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def ok(msg: str)   -> None: print(f"{GREEN}✓  {msg}{RESET}")
def info(msg: str) -> None: print(f"{CYAN}->  {msg}{RESET}")
def warn(msg: str) -> None: print(f"{YELLOW}⚠  {msg}{RESET}")
def err(msg: str)  -> None: print(f"{RED}✗  {msg}{RESET}", file=sys.stderr)
def step(n: int, title: str) -> None:
    print(f"\n{BOLD}[{n}] {title}{RESET}")


def pretty(data: dict) -> None:
    print(json.dumps(data, indent=2, default=str))


def die(msg: str, code: int = 1) -> None:
    err(msg)
    sys.exit(code)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({"Content-Type": "application/json", "Accept": "application/json"})


def post(url: str, payload: dict, *, headers: dict | None = None, label: str = "POST") -> dict:
    try:
        r = SESSION.post(url, json=payload, headers=headers, timeout=10)
    except requests.ConnectionError:
        die(f"Cannot reach {url} — is the server running?")

    if not r.ok:
        die(f"{label} {url} failed [{r.status_code}]: {r.text}")
    return r.json()


def get(url: str, *, headers: dict | None = None, label: str = "GET") -> dict:
    try:
        r = SESSION.get(url, headers=headers, timeout=10)
    except requests.ConnectionError:
        die(f"Cannot reach {url} — is the server running?")

    if not r.ok:
        die(f"{label} {url} failed [{r.status_code}]: {r.text}")
    return r.json()


# ---------------------------------------------------------------------------
# Step 1 — Login
# ---------------------------------------------------------------------------

def login(base_url: str, username: str, password: str) -> str:
    """POST /auth/login -> return access token."""
    step(1, "Admin login")
    info(f"Authenticating as '{username}' …")

    data = post(
        f"{base_url}/auth/login",
        {"username": username, "password": password},
        label="LOGIN",
    )

    token = data.get("access_token")
    if not token:
        die(f"Login response missing access_token: {data}")

    ok("Authenticated — access token received")
    return token


# ---------------------------------------------------------------------------
# Step 2 — Create API key
# ---------------------------------------------------------------------------

def create_api_key(base_url: str, access_token: str, key_name: str = "example-script") -> str:
    """POST /admin/api-keys -> return raw API key."""
    step(2, "Create API key")
    info(f"Creating API key '{key_name}' …")

    auth_header = {"Authorization": f"Bearer {access_token}"}
    data = post(
        f"{base_url}/admin/api-keys",
        {"name": key_name},
        headers=auth_header,
        label="CREATE_API_KEY",
    )

    raw_key = data.get("raw_key")
    if not raw_key:
        die(f"API key response missing raw_key: {data}")

    ok(f"API key created  ->  id: {data['id']}")
    ok(f"Raw key (shown once, store it safely): {BOLD}{raw_key}{RESET}")
    return raw_key


# ---------------------------------------------------------------------------
# Step 3 — Create payment
# ---------------------------------------------------------------------------

def create_payment(
    base_url: str,
    api_key: str,
    chain: str,
    amount: int,
    token_contract_address: str | None = None,
) -> dict:
    """POST /api/v1/payments/ -> return payment record."""
    step(3, "Create payment")

    payload: dict = {"chain": chain, "amount": amount}
    if token_contract_address:
        payload["token_contract_address"] = token_contract_address
        info(f"ERC-20 payment  token={token_contract_address}  amount={amount}")
    else:
        info(f"Native payment  chain={chain}  amount={amount} wei ({amount / 1e18:.6f} ETH)")

    data = post(
        f"{base_url}/api/v1/payments/",
        payload,
        headers={"X-Api-Key": api_key},
        label="CREATE_PAYMENT",
    )

    ok(f"Payment created  ->  id: {data['id']}")
    ok(f"Receiving address: {data['address']}")
    ok(f"Expires at: {data['expires_at']}")
    return data


# ---------------------------------------------------------------------------
# Step 4 — Send on-chain transaction
# ---------------------------------------------------------------------------

def send_transaction(rpc_url: str, sender_key: str, to_address: str, value_wei: int) -> str:
    """Sign and broadcast a native ETH transfer; returns the tx hash."""
    step(4, "Send on-chain transaction")

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        die(f"Cannot connect to RPC node at {rpc_url}")

    sender = w3.eth.account.from_key(sender_key)
    info(f"Sender: {sender.address}")
    info(f"To:     {to_address}")
    info(f"Value:  {value_wei} wei ({value_wei / 1e18:.6f} ETH)")

    nonce       = w3.eth.get_transaction_count(sender.address, "pending")
    gas_price   = w3.eth.gas_price
    chain_id    = w3.eth.chain_id

    tx = {
        "to":       to_address,
        "value":    value_wei,
        "gas":      21_000,
        "gasPrice": gas_price,
        "nonce":    nonce,
        "chainId":  chain_id,
    }

    signed = w3.eth.account.sign_transaction(tx, sender_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    hex_hash = w3.to_hex(tx_hash)

    ok(f"Transaction broadcast  ->  {hex_hash}")
    return hex_hash


# ---------------------------------------------------------------------------
# Step 5 — Poll payment status
# ---------------------------------------------------------------------------

def poll_payment(
    base_url: str,
    api_key: str,
    payment_id: str,
    *,
    target_statuses: tuple = ("detected", "confirmed", "paid", "settled"),
    timeout: int = 120,
    interval: int = 3,
) -> dict:
    """GET /api/v1/payments/{id} until a terminal status is reached."""
    step(5, "Poll payment status")

    url = f"{base_url}/api/v1/payments/{payment_id}"
    headers = {"X-Api-Key": api_key}
    deadline = time.time() + timeout
    last_status = None

    while time.time() < deadline:
        data = get(url, headers=headers, label="GET_PAYMENT")
        status = data.get("status", "unknown")

        if status != last_status:
            info(f"Status: {BOLD}{status}{RESET}")
            last_status = status

        if status in target_statuses:
            ok(f"Payment reached '{status}' ✓")
            return data

        if status in ("expired", "failed"):
            warn(f"Payment ended with non-success status: {status}")
            return data

        time.sleep(interval)

    warn(f"Timed out after {timeout}s — last status: {last_status}")
    return {}


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="End-to-end payment simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--base-url",    default=DEFAULTS["base_url"],    help="API base URL")
    p.add_argument("--rpc-url",     default=DEFAULTS["rpc_url"],     help="EVM RPC URL")
    p.add_argument("--username",    default=DEFAULTS["username"],     help="Admin username")
    p.add_argument("--password",    default=DEFAULTS["password"],     help="Admin password")
    p.add_argument("--sender-key",  default=DEFAULTS["sender_key"],  help="Sender private key (hex)")
    p.add_argument("--amount",      default=DEFAULTS["amount"],      type=int, help="Payment amount in wei")
    p.add_argument("--chain",       default=DEFAULTS["chain"],       help="Chain name")
    p.add_argument("--token",       default=None,                    help="ERC-20 contract address (omit for native)")
    p.add_argument("--key-name",    default="example-script",        help="Label for the generated API key")
    p.add_argument("--no-tx",       action="store_true",             help="Skip sending the on-chain transaction")
    p.add_argument("--poll-timeout",default=120, type=int,           help="Seconds to wait for payment detection")
    return p.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()

    print(f"\n{BOLD}{'─' * 60}")
    print("  ctrip  —  payment simulation")
    print(f"{'─' * 60}{RESET}")
    print(f"  API:   {args.base_url}")
    print(f"  RPC:   {args.rpc_url}")
    print(f"  Chain: {args.chain}")
    print(f"  Amount:{args.amount} wei ({args.amount / 1e18:.6f} ETH)")
    if args.token:
        print(f"  Token: {args.token}")
    print()

    # 1 — authenticate
    access_token = login(args.base_url, args.username, args.password)

    # 2 — provision an API key
    api_key = create_api_key(args.base_url, access_token, key_name=args.key_name)

    # 3 — create payment
    payment = create_payment(
        args.base_url,
        api_key,
        chain=args.chain,
        amount=args.amount,
        token_contract_address=args.token,
    )

    # 4 — send funds (skippable for manual testing)
    if args.no_tx:
        warn("Skipping on-chain transaction (--no-tx)")
    else:
        tx_hash = send_transaction(
            args.rpc_url,
            args.sender_key,
            to_address=payment["address"],
            value_wei=args.amount,
        )
        print(f"\n  Tx hash: {tx_hash}")

    # 5 — poll until detected / confirmed
    final = poll_payment(
        args.base_url,
        api_key,
        payment_id=payment["id"],
        timeout=args.poll_timeout,
    )

    if final:
        print(f"\n{BOLD}Final payment state:{RESET}")
        pretty(final)

    print(f"\n{BOLD}{'─' * 60}{RESET}\n")


if __name__ == "__main__":
    main()
