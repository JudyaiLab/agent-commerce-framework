"""
End-to-end payment flow smoke test.

Tests the complete buyer journey:
1. Check balance (should be 0)
2. Credit test balance (admin endpoint)
3. List available services
4. Call a service through proxy (free tier)
5. Call again (paid, deducts from balance)
6. Verify balance was deducted

Usage:
    python test_flow.py                    # Uses config.yaml
    python test_flow.py --config my.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from sdk.client import ACFClient


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def run_smoke_test(config: dict) -> bool:
    marketplace = config["marketplace"]
    base_url = marketplace["url"]
    api_key = marketplace["api_key"]

    client = ACFClient(base_url=base_url, api_key=api_key)
    buyer_id = "smoke-test-buyer"
    passed = 0
    total = 0

    def check(name: str, condition: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}")
        else:
            print(f"  [FAIL] {name} — {detail}")

    print("=" * 50)
    print("AgenticTrade Payment Flow Smoke Test")
    print("=" * 50)

    # 1. Check initial balance
    print("\n[1/6] Checking initial balance...")
    try:
        import httpx
        resp = httpx.get(f"{base_url}/api/v1/balance/{buyer_id}")
        data = resp.json()
        check("Initial balance is 0", data.get("balance", -1) == 0)
    except Exception as e:
        check("Balance endpoint reachable", False, str(e))

    # 2. Credit test balance
    print("\n[2/6] Crediting test balance ($5)...")
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/admin/credit",
            params={"buyer_id": buyer_id, "amount": 5.0, "admin_key": "test-admin-secret"},
        )
        data = resp.json()
        check("Admin credit successful", resp.status_code == 200, f"status={resp.status_code}")
        check("Balance is $5", data.get("new_balance", 0) == 5.0, f"got {data.get('new_balance')}")
    except Exception as e:
        check("Admin credit endpoint", False, str(e))

    # 3. List services
    print("\n[3/6] Listing marketplace services...")
    try:
        services = client.list_services()
        check("Services listed", len(services) > 0, "no services found")
        if services:
            svc = services[0]
            svc_id = svc["id"]
            print(f"         Using: {svc['name']} (${svc.get('price_per_call', '?')}/call)")
    except Exception as e:
        check("Service listing", False, str(e))
        return False

    # 4. Free tier call
    print("\n[4/6] Making free tier call...")
    try:
        resp = httpx.post(
            f"{base_url}/api/v1/proxy/{svc_id}/test",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"test": True},
            params={"buyer_id": buyer_id},
        )
        free_tier = resp.headers.get("X-ACF-Free-Tier", "unknown")
        check("Proxy call succeeded", resp.status_code in (200, 201, 204), f"status={resp.status_code}")
        check("Free tier used", free_tier == "true", f"X-ACF-Free-Tier={free_tier}")
    except Exception as e:
        check("Free tier proxy call", False, str(e))

    # 5. Exhaust free tier + paid call
    print("\n[5/6] Making paid call (after free tier)...")
    try:
        # Exhaust remaining free calls
        for _ in range(10):
            r = httpx.post(
                f"{base_url}/api/v1/proxy/{svc_id}/test",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"test": True},
                params={"buyer_id": buyer_id},
            )
            if r.headers.get("X-ACF-Free-Tier") == "false":
                break

        amount = r.headers.get("X-ACF-Amount", "0")
        check("Paid call succeeded", r.status_code in (200, 201, 204), f"status={r.status_code}")
        check("Amount charged", float(amount) > 0, f"X-ACF-Amount={amount}")
    except Exception as e:
        check("Paid proxy call", False, str(e))

    # 6. Verify balance deducted
    print("\n[6/6] Verifying balance deduction...")
    try:
        resp = httpx.get(f"{base_url}/api/v1/balance/{buyer_id}")
        data = resp.json()
        balance = data.get("balance", 5.0)
        check("Balance deducted", balance < 5.0, f"balance={balance} (expected < 5.0)")
    except Exception as e:
        check("Balance check", False, str(e))

    print(f"\n{'=' * 50}")
    print(f"Results: {passed}/{total} passed")
    print("=" * 50)
    return passed == total


def main():
    parser = argparse.ArgumentParser(description="Smoke test AgenticTrade payment flow")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    args = parser.parse_args()

    config = load_config(args.config)
    success = run_smoke_test(config)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
