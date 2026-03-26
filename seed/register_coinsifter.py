"""
Register CoinSifter as the first real service on AgenticTrade.io.

Run from project root:
    .venv/bin/python seed/register_coinsifter.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set internal hosts before importing proxy
os.environ.setdefault("ACF_INTERNAL_HOSTS", "172.18.0.1,127.0.0.1")

from marketplace.db import Database
from marketplace.registry import ServiceRegistry
from marketplace.auth import APIKeyManager
from marketplace.identity import IdentityManager

BASE_URL = os.environ.get("ACF_BASE_URL", "https://agentictrade.io")
DB_PATH = os.environ.get("DATABASE_PATH", "data/marketplace.db")

db = Database(DB_PATH)
registry = ServiceRegistry(db)
key_mgr = APIKeyManager(db)
identity_mgr = IdentityManager(db)


def setup():
    """Register CoinSifter service on the platform."""

    # 1. Create platform admin key
    print("=== Creating Platform Admin ===")
    try:
        key_id, secret = key_mgr.create_key(
            owner_id="judyailab",
            role="admin",
        )
        print(f"  Admin Key ID: {key_id}")
        print(f"  Admin Secret: {secret[:8]}{'*' * 24}")
        print(f"  SAVE THIS! Won't be shown again.")
    except Exception as e:
        print(f"  Admin key exists or error: {e}")

    # 2. Create provider identity for JudyAI Lab
    print("\n=== Creating Provider Identity ===")
    try:
        agent = identity_mgr.register(
            owner_id="judyailab",
            display_name="JudyAI Lab",
            identity_type="api_key_only",
            capabilities=["crypto-scanning", "market-analysis", "technical-indicators"],
        )
        print(f"  Agent ID: {agent.agent_id}")
        print(f"  Display Name: {agent.display_name}")
    except Exception as e:
        print(f"  Identity exists or error: {e}")

    # 3. Create provider API key
    print("\n=== Creating Provider Key ===")
    try:
        key_id, secret = key_mgr.create_key(
            owner_id="judyailab",
            role="provider",
        )
        print(f"  Provider Key ID: {key_id}")
        print(f"  Provider Secret: {secret[:8]}{'*' * 24}")
    except Exception as e:
        print(f"  Provider key exists or error: {e}")

    # 4. Register CoinSifter Scan service
    print("\n=== Registering CoinSifter Scan Service ===")
    try:
        svc = registry.register(
            name="CoinSifter — Crypto Market Scanner",
            description=(
                "AI-powered cryptocurrency market scanner. "
                "Scans Binance USDT pairs with customizable technical indicators "
                "(RSI, EMA, MACD, Bollinger Bands, KD, Volume, ATR). "
                "Supports 8 indicators, 4 timeframes (15m/1h/4h/1d), "
                "and configurable filter logic (AND/OR). "
                "Returns detailed pass/fail analysis with human-readable reasons."
            ),
            endpoint="http://172.18.0.1:8089",
            provider_id="judyailab",
            category="crypto-analysis",
            tags=["crypto", "scanner", "technical-analysis", "binance", "market-data"],
            price_per_call="0.50",
            payment_method="nowpayments",
            free_tier_calls=5,
        )
        print(f"  Service ID: {svc.id}")
        print(f"  Name: {svc.name}")
        print(f"  Price: ${svc.pricing.price_per_call}/call")
        print(f"  Free tier: {svc.pricing.free_tier_calls} calls")
    except Exception as e:
        print(f"  Error: {e}")

    # 5. Register CoinSifter Demo service (free)
    print("\n=== Registering CoinSifter Demo Service ===")
    try:
        demo_svc = registry.register(
            name="CoinSifter Demo — Sample Results",
            description=(
                "Free demo endpoint returning sample CoinSifter scan results. "
                "No Binance API key required. Test integration before upgrading."
            ),
            endpoint="http://172.18.0.1:8089",
            provider_id="judyailab",
            category="crypto-analysis",
            tags=["crypto", "scanner", "demo", "free"],
            price_per_call="0",
            payment_method="nowpayments",
        )
        print(f"  Service ID: {demo_svc.id}")
        print(f"  Name: {demo_svc.name}")
        print(f"  Price: FREE")
    except Exception as e:
        print(f"  Error: {e}")

    # 6. Create a test buyer key
    print("\n=== Creating Test Buyer Key ===")
    try:
        key_id, secret = key_mgr.create_key(
            owner_id="test-buyer",
            role="buyer",
        )
        print(f"  Buyer Key ID: {key_id}")
        print(f"  Buyer Secret: {secret[:8]}{'*' * 24}")
    except Exception as e:
        print(f"  Buyer key exists or error: {e}")

    print("\n" + "=" * 50)
    print("SETUP COMPLETE")
    print("=" * 50)
    print(f"\nPlatform:  {BASE_URL}")
    print(f"API Docs:  {BASE_URL}/docs")
    print(f"Dashboard: {BASE_URL}/admin/dashboard?key=<admin_key_id>:<secret>")


if __name__ == "__main__":
    setup()
