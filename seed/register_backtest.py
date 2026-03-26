"""
Register Backtest-as-a-Service on the Agent Commerce Marketplace.

Run from project root:
    .venv/bin/python seed/register_backtest.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("ACF_INTERNAL_HOSTS", "172.18.0.1,127.0.0.1")

from marketplace.db import Database
from marketplace.registry import ServiceRegistry

DB_PATH = os.environ.get("DATABASE_PATH", "data/marketplace.db")

db = Database(DB_PATH)
registry = ServiceRegistry(db)


def setup():
    """Register backtest services on the platform."""

    # 1. Backtest API — paid service ($2/call, 3 free)
    print("=== Registering Backtest API Service ===")
    try:
        svc = registry.register(
            name="Strategy Backtest API",
            description=(
                "Run backtests with pre-built crypto trading strategies. "
                "3 strategies: BB Squeeze (momentum), MACD Divergence (reversal), "
                "RSI Mean Reversion (ranging markets). "
                "Returns: win rate, profit factor, equity curve, trade list. "
                "Supports custom parameters, multiple timeframes (15m/1h/4h/1d), "
                "and realistic simulation (fees + slippage)."
            ),
            endpoint="http://172.18.0.1:8090",
            provider_id="judyailab",
            category="trading-tools",
            tags=["backtest", "trading", "strategy", "crypto", "technical-analysis"],
            price_per_call="2.00",
            payment_method="nowpayments",
            free_tier_calls=3,
        )
        print(f"  Service ID: {svc.id}")
        print(f"  Name: {svc.name}")
        print(f"  Price: ${svc.pricing.price_per_call}/call")
        print(f"  Free tier: {svc.pricing.free_tier_calls} calls")
    except Exception as e:
        print(f"  Error: {e}")

    # 2. Strategy Catalog — free (list strategies only)
    print("\n=== Registering Strategy Catalog (Free) ===")
    try:
        cat_svc = registry.register(
            name="Strategy Catalog — Browse Templates",
            description=(
                "Browse available trading strategy templates and their "
                "configurable parameters. Free to access."
            ),
            endpoint="http://172.18.0.1:8090",
            provider_id="judyailab",
            category="trading-tools",
            tags=["strategy", "catalog", "free"],
            price_per_call="0",
            payment_method="nowpayments",
        )
        print(f"  Service ID: {cat_svc.id}")
        print(f"  Name: {cat_svc.name}")
        print(f"  Price: FREE")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 50)
    print("BACKTEST SERVICE REGISTERED")
    print("=" * 50)
    print("\nUsage:")
    print("  1. Start API: cd ~/projects/judy-crypto && uvicorn backtest_api:app --port 8090")
    print("  2. Browse strategies: GET /strategies")
    print("  3. Run backtest: POST /backtest {strategy, symbol, days, params}")
    print("  4. Get results: GET /backtest/{job_id}")


if __name__ == "__main__":
    setup()
