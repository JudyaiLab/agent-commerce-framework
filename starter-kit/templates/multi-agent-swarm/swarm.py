"""
Multi-Agent Swarm — 5 agents trading autonomously on the AgenticTrade marketplace.

This demonstrates a complete agent economy:
  1. Discovery Agent searches for services
  2. Quality Agent filters by reputation
  3. Buyer Agent purchases and calls services
  4. Orchestrator coordinates the workflow
  5. Reporter tracks transactions and ROI

Usage:
    python swarm.py                    # Uses config.yaml
    python swarm.py --config my.yaml
    python swarm.py --budget 5.00      # Override budget limit
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from sdk.client import ACFClient


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ServiceCandidate:
    id: str
    name: str
    price: float
    free_tier: int
    category: str
    reputation: float = 0.0


@dataclass(frozen=True)
class Transaction:
    service_id: str
    service_name: str
    amount: float
    free_tier: bool
    timestamp: str
    success: bool
    response_snippet: str = ""


@dataclass
class SwarmState:
    budget_limit: float
    total_spent: float = 0.0
    transactions: list[Transaction] = field(default_factory=list)
    discovered: list[ServiceCandidate] = field(default_factory=list)
    qualified: list[ServiceCandidate] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class DiscoveryAgent:
    """Searches the marketplace for services matching criteria."""

    def __init__(self, client: ACFClient, categories: list[str]):
        self.client = client
        self.categories = categories

    def search(self) -> list[ServiceCandidate]:
        print("\n[Discovery] Searching marketplace...")
        services = self.client.list_services()
        candidates = []
        for svc in services:
            candidate = ServiceCandidate(
                id=svc["id"],
                name=svc["name"],
                price=float(svc.get("price_per_call", 0)),
                free_tier=int(svc.get("free_tier_calls", 0)),
                category=svc.get("category", ""),
            )
            candidates.append(candidate)
            print(f"  Found: {candidate.name} (${candidate.price}/call, {candidate.free_tier} free)")
        print(f"[Discovery] Found {len(candidates)} services")
        return candidates


class QualityAgent:
    """Filters services by reputation score."""

    def __init__(self, client: ACFClient, min_reputation: float = 3.5):
        self.client = client
        self.min_reputation = min_reputation

    def evaluate(self, candidates: list[ServiceCandidate]) -> list[ServiceCandidate]:
        print(f"\n[Quality] Evaluating {len(candidates)} services (min rep: {self.min_reputation})...")
        qualified = []
        for c in candidates:
            try:
                rep = self.client.get_reputation(c.id)
                score = float(rep.get("average_score", 5.0))
            except Exception:
                score = 5.0  # Default for new services

            updated = ServiceCandidate(
                id=c.id, name=c.name, price=c.price,
                free_tier=c.free_tier, category=c.category,
                reputation=score,
            )

            if score >= self.min_reputation:
                qualified.append(updated)
                print(f"  [PASS] {c.name} (rep: {score:.1f})")
            else:
                print(f"  [SKIP] {c.name} (rep: {score:.1f} < {self.min_reputation})")

        print(f"[Quality] {len(qualified)}/{len(candidates)} passed quality check")
        return qualified


class BuyerAgent:
    """Executes purchases through the payment proxy."""

    def __init__(self, client: ACFClient, buyer_id: str, min_balance: float = 1.0):
        self.client = client
        self.buyer_id = buyer_id
        self.min_balance = min_balance

    def get_balance(self) -> float:
        try:
            import httpx
            resp = httpx.get(
                f"{self.client.base_url}/api/v1/balance/{self.buyer_id}"
            )
            return float(resp.json().get("balance", 0))
        except Exception:
            return 0.0

    def buy(self, service: ServiceCandidate, payload: dict | None = None) -> Transaction:
        """Call a service through the proxy and return the transaction."""
        now = datetime.now(timezone.utc).isoformat()
        balance = self.get_balance()

        if balance < self.min_balance and service.price > 0:
            print(f"  [BuyerAgent] Balance too low (${balance:.2f}), skipping paid service")
            return Transaction(
                service_id=service.id, service_name=service.name,
                amount=0, free_tier=False, timestamp=now, success=False,
                response_snippet="insufficient_balance",
            )

        try:
            import httpx
            resp = httpx.post(
                f"{self.client.base_url}/api/v1/proxy/{service.id}/request",
                headers=self.client._headers(),
                json=payload or {"source": "swarm"},
                params={"buyer_id": self.buyer_id},
                timeout=30,
            )
            amount = float(resp.headers.get("X-ACF-Amount", "0"))
            free = resp.headers.get("X-ACF-Free-Tier", "false") == "true"
            snippet = resp.text[:100] if resp.text else ""

            return Transaction(
                service_id=service.id, service_name=service.name,
                amount=amount, free_tier=free, timestamp=now,
                success=resp.status_code < 400, response_snippet=snippet,
            )
        except Exception as e:
            return Transaction(
                service_id=service.id, service_name=service.name,
                amount=0, free_tier=False, timestamp=now, success=False,
                response_snippet=str(e)[:100],
            )


class Reporter:
    """Tracks all transactions and computes ROI."""

    def __init__(self, log_file: str = "swarm_transactions.jsonl"):
        self.log_file = log_file

    def record(self, tx: Transaction):
        with open(self.log_file, "a") as f:
            f.write(json.dumps({
                "service_id": tx.service_id,
                "service_name": tx.service_name,
                "amount": tx.amount,
                "free_tier": tx.free_tier,
                "success": tx.success,
                "timestamp": tx.timestamp,
            }) + "\n")

    def summary(self, state: SwarmState):
        print(f"\n{'=' * 60}")
        print("SWARM EXECUTION REPORT")
        print("=" * 60)
        print(f"  Services discovered: {len(state.discovered)}")
        print(f"  Services qualified:  {len(state.qualified)}")
        print(f"  Transactions:        {len(state.transactions)}")
        successful = [t for t in state.transactions if t.success]
        failed = [t for t in state.transactions if not t.success]
        free = [t for t in successful if t.free_tier]
        paid = [t for t in successful if not t.free_tier]
        print(f"  Successful:          {len(successful)}")
        print(f"  Failed:              {len(failed)}")
        print(f"  Free tier calls:     {len(free)}")
        print(f"  Paid calls:          {len(paid)}")
        print(f"  Total spent:         ${state.total_spent:.2f}")
        print(f"  Budget remaining:    ${state.budget_limit - state.total_spent:.2f}")
        print("=" * 60)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class Orchestrator:
    """Coordinates the multi-agent swarm."""

    def __init__(
        self,
        client: ACFClient,
        config: dict,
    ):
        swarm_cfg = config.get("swarm", {})
        buyer_cfg = config.get("buyer", {})
        reporter_cfg = config.get("reporter", {})

        self.state = SwarmState(budget_limit=swarm_cfg.get("budget_limit", 10.0))
        self.discovery = DiscoveryAgent(client, swarm_cfg.get("search_categories", []))
        self.quality = QualityAgent(client, swarm_cfg.get("min_reputation", 3.5))
        self.buyer = BuyerAgent(client, buyer_cfg.get("buyer_id", "swarm-buyer"), buyer_cfg.get("min_balance", 1.0))
        self.reporter = Reporter(reporter_cfg.get("log_file", "swarm_transactions.jsonl"))

    def run(self):
        print("=" * 60)
        print("MULTI-AGENT SWARM — Starting")
        print(f"Budget: ${self.state.budget_limit:.2f}")
        print("=" * 60)

        # Phase 1: Discovery
        self.state.discovered = self.discovery.search()
        if not self.state.discovered:
            print("\n[Orchestrator] No services found. Exiting.")
            return

        # Phase 2: Quality filter
        self.state.qualified = self.quality.evaluate(self.state.discovered)
        if not self.state.qualified:
            print("\n[Orchestrator] No services passed quality check. Exiting.")
            return

        # Phase 3: Buy from qualified services
        print(f"\n[Orchestrator] Buying from {len(self.state.qualified)} qualified services...")
        for svc in self.state.qualified:
            if self.state.total_spent >= self.state.budget_limit:
                print(f"\n[Orchestrator] Budget limit reached (${self.state.budget_limit:.2f}). Stopping.")
                break

            print(f"\n  Calling: {svc.name}...")
            tx = self.buyer.buy(svc)

            self.state.transactions.append(tx)
            self.state.total_spent += tx.amount
            self.reporter.record(tx)

            status = "OK" if tx.success else "FAIL"
            cost = f"${tx.amount:.2f}" if not tx.free_tier else "FREE"
            print(f"  Result: [{status}] {cost} — {tx.response_snippet[:60]}")

            time.sleep(0.5)  # Rate limit courtesy

        # Phase 4: Report
        self.reporter.summary(self.state)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run the multi-agent swarm")
    parser.add_argument("--config", default="config.yaml", help="Config file")
    parser.add_argument("--budget", type=float, help="Override budget limit")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        print("Copy config.example.yaml to config.yaml and customize it.")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    if args.budget:
        config.setdefault("swarm", {})["budget_limit"] = args.budget

    marketplace = config["marketplace"]
    client = ACFClient(
        base_url=marketplace["url"],
        api_key=marketplace["api_key"],
    )

    orchestrator = Orchestrator(client, config)
    orchestrator.run()


if __name__ == "__main__":
    main()
