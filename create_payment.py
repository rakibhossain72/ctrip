import requests
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter

def make_payment():
    url = "http://127.0.0.1:8000/api/v1/payments/"
    payload = {
        "amount": 100000000000,
        "chain": "anvil"
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json(), response.status_code
    except Exception as e:
        return {"error": str(e)}, getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None

def main():
    pay_count = 10000
    start = perf_counter()
    
    results = []
    successes = 0
    
    # Adjust max_workers depending on your server
    # localhost anvil/fastapi → usually 20–40 is sweet spot
    with ThreadPoolExecutor(max_workers=30) as executor:
        future_to_idx = {executor.submit(make_payment): i for i in range(pay_count)}
        
        for future in as_completed(future_to_idx):
            result, status = future.result()
            results.append(result)
            
            if status is not None and 200 <= status < 300:
                successes += 1
                print(result)           # or log / save
            else:
                print(f"Failed: {result} (status={status})")
    
    elapsed = perf_counter() - start
    print(f"\nFinished {pay_count} requests in {elapsed:.2f} seconds")
    print(f"Successful: {successes}/{pay_count}  ({successes/pay_count*100:.1f}%)")

if __name__ == "__main__":
    main()