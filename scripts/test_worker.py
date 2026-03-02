#!/usr/bin/env python3
"""
Test script to verify worker setup and trigger test jobs.
"""
import asyncio
import sys
from app.workers.client import WorkerClient


async def test_worker():
    """Test worker connectivity and job submission"""
    client = WorkerClient()
    
    print("🧪 Testing ARQ Worker Setup")
    print("=" * 50)
    
    try:
        # Test 1: Get pool connection
        print("\n1️⃣  Testing Redis connection...")
        pool = await client.get_pool()
        print("   ✅ Connected to Redis")
        
        # Test 2: Trigger payment scan
        print("\n2️⃣  Triggering payment scan...")
        job_id = await client.trigger_payment_scan()
        print(f"   ✅ Job enqueued: {job_id}")
        
        # Wait a bit for job to process
        await asyncio.sleep(2)
        
        
        # Test 3: Trigger sweep
        print("\n3️⃣  Triggering fund sweep...")
        sweep_job_id = await client.trigger_sweep()
        print(f"   ✅ Sweep job enqueued: {sweep_job_id}")
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("\nWorker is configured correctly and accepting jobs.")
        print("Check worker logs to see job execution.")
        
    except Exception as e:
        # raise e
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure Redis is running: redis-cli ping")
        print("2. Make sure worker is running: python run_worker.py")
        print("3. Check REDIS_URL in .env file")
        sys.exit(1)
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_worker())
