"""
Example requests for creating a payment
"""


import json
import requests
import web3

RPC_URL = "http://127.0.0.1:8545"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
w3 = web3.Web3(web3.Web3.HTTPProvider(RPC_URL))

URL = "http://127.0.0.1:8000/api/v1/payments/"

payload = json.dumps({
  "amount": 100000000000,
  "chain": "anvil"
})
headers = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
}

response = requests.request("POST", URL, headers=headers, data=payload, timeout=10)


if response.status_code == 201:
    payment = response.json()
    print("Payment created successfully:")
    print(json.dumps(payment, indent=4))

    tx = {
        'to': payment['address'],
        'value': int(payment['amount']),
        'gas': 21000,
        'gasPrice': w3.to_wei('50', 'gwei'),
        'nonce': w3.eth.get_transaction_count(w3.eth.account.from_key(PRIVATE_KEY).address),
        'chainId': w3.eth.chain_id
    }

    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent with hash: {w3.to_hex(tx_hash)}")


    # fetch updated payment status
    payment_id = payment['id']
    GET_URL = f"{URL}{payment_id}/"
    get_response = requests.request("GET", GET_URL, headers=headers, timeout=10)
    if get_response.status_code == 200:
        updated_payment = get_response.json()
        print("Updated Payment Status:")
        print(json.dumps(updated_payment, indent=4))
else:
    print(f"Failed to create payment. Status code: {response.status_code}")
