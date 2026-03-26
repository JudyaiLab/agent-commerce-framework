"""
Seed demo data for the Agent Commerce Framework.

Populates the database with sample agents, services, usage records,
and teams so the admin dashboard and API have data to display.

Run: python -m seed.demo_data
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from marketplace.db import Database
from marketplace.registry import ServiceRegistry
from marketplace.auth import APIKeyManager
from marketplace.identity import IdentityManager
from marketplace.reputation import ReputationEngine


def _mask(secret: str) -> str:
    """Show first 4 chars of a secret, mask the rest."""
    if len(secret) <= 4:
        return secret
    return secret[:4] + "***"


def seed(db_path: str | None = None, *, show_secrets: bool = False):
    """Populate database with demo data.

    Set *show_secrets* to True (or pass ``--show-secrets`` on the CLI)
    to print raw API secrets.  By default secrets are masked.
    """
    db = Database(db_path)
    registry = ServiceRegistry(db)
    auth = APIKeyManager(db)
    identity = IdentityManager(db)
    reputation = ReputationEngine(db)

    def _fmt_key(key_id: str, secret: str) -> str:
        displayed = secret if show_secrets else _mask(secret)
        return f"{key_id}:{displayed}"

    print("Seeding demo data...")

    # --- Admin key ---
    admin_key_id, admin_secret = auth.create_key(
        owner_id="admin", role="admin"
    )
    print(f"  Admin key: {_fmt_key(admin_key_id, admin_secret)}")

    # --- Provider agents + keys ---
    providers = [
        {
            "display_name": "CoinSifter Bot",
            "owner_id": "provider-coinsifter",
            "capabilities": ["crypto-analysis", "market-data", "technical-analysis"],
        },
        {
            "display_name": "DataPipe AI",
            "owner_id": "provider-datapipe",
            "capabilities": ["data-processing", "etl", "csv-parsing"],
        },
        {
            "display_name": "ContentGen Pro",
            "owner_id": "provider-contentgen",
            "capabilities": ["text-generation", "summarization", "translation"],
        },
        {
            "display_name": "VisionAI Scanner",
            "owner_id": "provider-vision",
            "capabilities": ["image-analysis", "ocr", "object-detection"],
        },
    ]

    provider_keys = {}
    for p in providers:
        agent = identity.register(
            display_name=p["display_name"],
            owner_id=p["owner_id"],
            capabilities=p["capabilities"],
        )
        key_id, secret = auth.create_key(
            owner_id=p["owner_id"], role="provider"
        )
        provider_keys[p["owner_id"]] = f"{key_id}:{secret}"
        print(f"  Provider: {p['display_name']} ({p['owner_id']})")

    # --- Services ---
    services_data = [
        {
            "provider_id": "provider-coinsifter",
            "name": "CoinSifter Crypto Scanner",
            "description": "Real-time crypto market scanning with 100+ USDT pairs",
            "endpoint": "https://api.coinsifter.com/v1",
            "price_per_call": "0.01",
            "category": "crypto",
            "tags": ["ai", "crypto", "scanner", "trading"],
            "payment_method": "x402",
            "free_tier_calls": 50,
        },
        {
            "provider_id": "provider-coinsifter",
            "name": "CoinSifter Signal API",
            "description": "AI-powered trading signals with trend detection",
            "endpoint": "https://api.coinsifter.com/v1/signals",
            "price_per_call": "0.02",
            "category": "crypto",
            "tags": ["ai", "signals", "trading"],
            "payment_method": "x402",
            "free_tier_calls": 10,
        },
        {
            "provider_id": "provider-datapipe",
            "name": "DataPipe ETL Service",
            "description": "Transform and process data pipelines at scale",
            "endpoint": "https://api.datapipe.ai/process",
            "price_per_call": "0.10",
            "category": "data",
            "tags": ["etl", "data", "processing"],
            "payment_method": "nowpayments",
            "free_tier_calls": 25,
        },
        {
            "provider_id": "provider-contentgen",
            "name": "ContentGen Writer",
            "description": "AI content generation for blogs, social, and marketing",
            "endpoint": "https://api.contentgen.pro/generate",
            "price_per_call": "0.05",
            "category": "content",
            "tags": ["ai", "writing", "content", "marketing"],
            "payment_method": "stripe",
            "free_tier_calls": 20,
        },
        {
            "provider_id": "provider-vision",
            "name": "VisionAI Object Detector",
            "description": "Real-time object detection and image classification",
            "endpoint": "https://api.visionai.dev/detect",
            "price_per_call": "0.03",
            "category": "ai",
            "tags": ["vision", "ai", "detection", "image"],
            "payment_method": "x402",
            "free_tier_calls": 100,
        },
    ]

    service_ids = []
    for s in services_data:
        svc = registry.register(**s)
        service_ids.append(svc.id)
        print(f"  Service: {s['name']} (${s['price_per_call']}/call)")

    # --- Buyer agents ---
    buyers = [
        {"display_name": "Trading Bot Alpha", "owner_id": "buyer-alpha"},
        {"display_name": "Research Agent", "owner_id": "buyer-research"},
        {"display_name": "Content Manager Bot", "owner_id": "buyer-content"},
    ]

    for b in buyers:
        identity.register(
            display_name=b["display_name"],
            owner_id=b["owner_id"],
            capabilities=["trading"],
        )
        auth.create_key(owner_id=b["owner_id"], role="buyer")
        print(f"  Buyer: {b['display_name']}")

    # --- Usage records (simulated) ---
    import uuid
    import random
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    usage_count = 0

    for day_offset in range(30):
        day = now - timedelta(days=day_offset)
        # More usage on recent days
        calls_today = random.randint(5, 30) if day_offset < 7 else random.randint(1, 10)

        for _ in range(calls_today):
            svc_idx = random.randint(0, len(service_ids) - 1)
            buyer = random.choice(buyers)
            latency = random.randint(50, 800)
            status = random.choice([200] * 9 + [500])  # 90% success

            price = float(services_data[svc_idx]["price_per_call"])
            ts = day - timedelta(
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            record = {
                "id": str(uuid.uuid4()),
                "buyer_id": buyer["owner_id"],
                "service_id": service_ids[svc_idx],
                "provider_id": services_data[svc_idx]["provider_id"],
                "timestamp": ts.isoformat(),
                "latency_ms": latency,
                "status_code": status,
                "amount_usd": price if status < 500 else 0,
                "payment_method": services_data[svc_idx].get("payment_method", "x402"),
                "payment_tx": f"0x{uuid.uuid4().hex[:40]}",
            }
            db.insert_usage(record)
            usage_count += 1

    print(f"  Usage records: {usage_count}")

    # --- Compute reputation ---
    for p in providers:
        reputation.save_reputation(provider_id=p["owner_id"])

    print(f"  Reputation computed for {len(providers)} providers")

    # --- Teams ---
    import uuid as uuid_mod
    team_id = str(uuid_mod.uuid4())
    now_str = now.isoformat()

    db.insert_team({
        "id": team_id,
        "name": "AI Development Squad",
        "owner_id": "provider-coinsifter",
        "description": "Full-stack AI agent team",
        "config": {"routing_mode": "keyword"},
        "created_at": now_str,
        "updated_at": now_str,
    })

    for agent_id, role in [
        ("leader-agent", "leader"),
        ("coder-agent", "worker"),
        ("reviewer-agent", "reviewer"),
    ]:
        db.insert_team_member({
            "id": str(uuid_mod.uuid4()),
            "team_id": team_id,
            "agent_id": agent_id,
            "role": role,
            "skills": [role],
            "joined_at": now_str,
        })

    print(f"  Team: AI Development Squad (3 members)")

    print(f"\nDone! Admin key: {_fmt_key(admin_key_id, admin_secret)}")
    if show_secrets:
        print(f"Dashboard: http://localhost:8000/admin/dashboard?key={admin_key_id}:{admin_secret}")
    else:
        print("  (run with --show-secrets to display full credentials)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed demo data")
    parser.add_argument("db_path", nargs="?", default=None, help="SQLite DB path")
    parser.add_argument(
        "--show-secrets",
        action="store_true",
        help="Print raw API secrets (masked by default)",
    )
    args = parser.parse_args()
    seed(args.db_path, show_secrets=args.show_secrets)
