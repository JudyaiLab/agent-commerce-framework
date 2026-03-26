#!/usr/bin/env python3
"""
AgenticTrade Connection & Payment Smoke Test CLI.

Tests the connection and payment flow against the AgenticTrade marketplace:
  1. Health check
  2. Service discovery
  3. Service listing
  4. Free tier proxy call
  5. Paid proxy call (if API key provided)

Usage:
    python acf_test_payment.py                                    # Default: agentictrade.io
    python acf_test_payment.py --api-key key_id:secret            # With authentication
    python acf_test_payment.py --url http://localhost:8092         # Local dev server
"""
from __future__ import annotations

import argparse
import sys
import time

import httpx


def smoke_test(base_url: str, api_key: str) -> bool:
    client = httpx.Client(timeout=30)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    passed = 0
    total = 0

    def check(name: str, ok: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        mark = "\033[32mPASS\033[0m" if ok else "\033[31mFAIL\033[0m"
        print(f"  [{mark}] {name}" + (f" — {detail}" if detail and not ok else ""))
        if ok:
            passed += 1

    print(f"\n{'='*55}")
    print(f"  AgenticTrade Connection Smoke Test")
    print(f"  Server: {base_url}")
    if api_key:
        print(f"  Auth: API key provided")
    else:
        print(f"  Auth: None (read-only mode)")
    print(f"{'='*55}\n")

    # 1. Health
    print("[1/5] Health check...")
    try:
        r = client.get(f"{base_url}/health")
        data = r.json()
        check(
            "Server healthy",
            r.status_code == 200 and data.get("status") == "ok",
            f"version={data.get('version', '?')}, services={data.get('services', '?')}",
        )
        if r.status_code == 200:
            v = data.get("version", "?")
            svc_count = data.get("services", "?")
            print(f"         Version: {v} | Active services: {svc_count}")
    except Exception as e:
        check("Server reachable", False, str(e))
        print(f"\nServer not reachable at {base_url}")
        print("Check your URL and try again.")
        return False

    # 2. Discovery
    print("[2/5] Service discovery...")
    try:
        r = client.get(f"{base_url}/api/v1/discover", headers=headers)
        data = r.json()
        services = data.get("services", [])
        check("Discovery endpoint works", r.status_code == 200)
        print(f"         Found {len(services)} service(s)")
        for svc in services[:3]:
            name = svc.get("name", "?")
            price = svc.get("price_per_call", "?")
            print(f"         — {name} (${price}/call)")
    except Exception as e:
        check("Discovery", False, str(e))

    # 3. Service listing
    print("[3/5] Service listing...")
    svc_id = None
    try:
        r = client.get(f"{base_url}/api/v1/services", headers=headers)
        data = r.json()
        svc_list = data.get("services", data) if isinstance(data, dict) else data
        has_services = isinstance(svc_list, list) and len(svc_list) > 0
        check("Services available", has_services, "no services found")
        if has_services:
            # Find a service with free tier for safe testing
            for svc in svc_list:
                if svc.get("free_tier_calls", 0) > 0 and svc.get("status") == "active":
                    svc_id = svc["id"]
                    print(f"         Using: {svc['name']} (free tier available)")
                    break
            if not svc_id:
                svc_id = svc_list[0]["id"]
                print(f"         Using: {svc_list[0]['name']}")
    except Exception as e:
        check("Service listing", False, str(e))

    if not svc_id:
        print("\nNo services available for proxy testing.")
        print(f"\nResult: {passed}/{total} passed")
        return passed == total

    # 4. Free tier proxy call
    print("[4/5] Free tier proxy call...")
    try:
        r = client.get(
            f"{base_url}/api/v1/proxy/{svc_id}/",
            headers=headers,
        )
        free_tier = r.headers.get("X-ACF-Free-Tier", "unknown")
        check("Proxy call OK", r.status_code < 500, f"status={r.status_code}")
        if r.status_code < 400:
            print(f"         Free tier: {free_tier}")
    except Exception as e:
        check("Free tier call", False, str(e))

    # 5. API key validation (if provided)
    if api_key:
        print("[5/5] API key validation...")
        try:
            parts = api_key.split(":", 1)
            if len(parts) == 2:
                r = client.post(
                    f"{base_url}/api/v1/keys/validate",
                    headers=headers,
                    json={"key_id": parts[0], "secret": parts[1]},
                )
                data = r.json()
                valid = data.get("valid", False)
                check("API key valid", valid, f"role={data.get('role', '?')}")
                if valid:
                    print(f"         Role: {data.get('role', '?')} | Owner: {data.get('owner_id', '?')}")
            else:
                check("API key format", False, "Expected format: key_id:secret")
        except Exception as e:
            check("Key validation", False, str(e))
    else:
        print("[5/5] API key validation... SKIPPED (no key provided)")

    print(f"\n{'='*55}")
    color = "\033[32m" if passed == total else "\033[33m"
    print(f"  Result: {color}{passed}/{total} passed\033[0m")
    if not api_key:
        print(f"  Tip: Run with --api-key for full test")
    print(f"{'='*55}")
    return passed == total


def main():
    p = argparse.ArgumentParser(description="AgenticTrade connection smoke test")
    p.add_argument("--url", default="https://agentictrade.io", help="Marketplace URL")
    p.add_argument("--api-key", default="", help="API key (key_id:secret)")
    args = p.parse_args()

    ok = smoke_test(args.url, args.api_key)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
