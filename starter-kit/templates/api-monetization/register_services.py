"""
Register services on the AgenticTrade marketplace from a YAML config file.

Usage:
    python register_services.py                    # Uses config.yaml
    python register_services.py --config my.yaml   # Custom config
    python register_services.py --dry-run           # Preview without registering
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

# Add parent paths so SDK is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from sdk.client import ACFClient


def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def register_all(config: dict, dry_run: bool = False) -> list[dict]:
    """Register all services defined in config. Returns list of results."""
    marketplace = config["marketplace"]
    client = ACFClient(
        base_url=marketplace["url"],
        api_key=marketplace["api_key"],
    )

    results = []
    for svc in config.get("services", []):
        print(f"\n{'[DRY RUN] ' if dry_run else ''}Registering: {svc['name']}")
        print(f"  Endpoint:    {svc['endpoint']}")
        print(f"  Price:       ${svc['price_per_call']}/call")
        print(f"  Free tier:   {svc.get('free_tier_calls', 0)} calls")

        if dry_run:
            results.append({"name": svc["name"], "status": "dry_run"})
            continue

        try:
            result = client.register_service(
                name=svc["name"],
                description=svc["description"],
                endpoint=svc["endpoint"],
                price_per_call=svc["price_per_call"],
                auth_header=f"Bearer {marketplace['api_key']}",
                free_tier_calls=svc.get("free_tier_calls", 0),
                category=svc.get("category", ""),
                tags=svc.get("tags", []),
            )
            svc_id = result.get("id", "unknown")
            print(f"  Registered!  ID: {svc_id}")
            results.append({"name": svc["name"], "id": svc_id, "status": "ok"})
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append({"name": svc["name"], "status": "error", "error": str(e)})

    return results


def main():
    parser = argparse.ArgumentParser(description="Register services on AgenticTrade")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--dry-run", action="store_true", help="Preview without registering")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print("Copy config.example.yaml to config.yaml and customize it.")
        sys.exit(1)

    config = load_config(str(config_path))
    results = register_all(config, dry_run=args.dry_run)

    print(f"\n{'=' * 50}")
    ok = sum(1 for r in results if r["status"] == "ok")
    fail = sum(1 for r in results if r["status"] == "error")
    print(f"Results: {ok} registered, {fail} failed, {len(results)} total")

    if ok > 0 and not args.dry_run:
        print(f"\nYour services are live! Buyers can call them via:")
        for r in results:
            if r["status"] == "ok":
                print(f"  POST {config['marketplace']['url']}/api/v1/proxy/{r['id']}/...")


if __name__ == "__main__":
    main()
