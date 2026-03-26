# Chapter 9: Multi-Agent Swarms

## From Single Agent to Swarm

A single agent buying services is useful. A coordinated swarm of specialized agents buying, evaluating, and reporting on services is powerful.

This chapter shows you how to build a 5-agent swarm that autonomously manages a service portfolio:

```
┌─────────────────────────────────────────────┐
│              Orchestrator                     │
│  (coordinates all agents, manages budget)    │
└──────────┬──────┬──────┬──────┬─────────────┘
           │      │      │      │
     ┌─────▼┐ ┌──▼───┐ ┌▼────┐ ┌▼──────┐
     │Disco-│ │Qual- │ │Buy- │ │Report-│
     │very  │ │ity   │ │er   │ │er     │
     └──────┘ └──────┘ └─────┘ └───────┘
```

## The Five Agents

### 1. Discovery Agent

Finds new services matching your criteria:

```python
class DiscoveryAgent:
    """Searches marketplace for services matching criteria."""

    def __init__(self, acf_client, criteria):
        self.client = acf_client
        self.criteria = criteria

    async def discover(self):
        results = []
        for criterion in self.criteria:
            services = await self.client.get("/api/v1/services", params={
                "q": criterion["query"],
                "category": criterion.get("category", ""),
                "max_price": criterion.get("max_price", 1.0),
            })
            results.extend(services.json())

        # Deduplicate by ID
        seen = set()
        unique = []
        for svc in results:
            if svc["id"] not in seen:
                seen.add(svc["id"])
                unique.append(svc)

        return unique
```

### 2. Quality Agent

Evaluates service quality using free tier calls:

```python
class QualityAgent:
    """Tests service quality using free tier calls."""

    def __init__(self, acf_client, buyer_id):
        self.client = acf_client
        self.buyer_id = buyer_id

    async def evaluate(self, service):
        scores = {
            "availability": 0,
            "latency_ms": 0,
            "data_quality": 0,
        }

        # Test with free tier calls
        test_calls = min(3, service["free_tier_calls"])
        latencies = []
        successes = 0

        for _ in range(test_calls):
            start = time.monotonic()
            try:
                r = await self.client.post(
                    f"/api/v1/proxy/{service['id']}/test",
                    json={"test": True},
                    params={"buyer_id": self.buyer_id},
                )
                latency = (time.monotonic() - start) * 1000
                latencies.append(latency)
                if r.status_code < 400:
                    successes += 1
            except Exception:
                pass

        if test_calls > 0:
            scores["availability"] = successes / test_calls
            scores["latency_ms"] = sum(latencies) / len(latencies) if latencies else 9999

        # Simple data quality heuristic
        scores["data_quality"] = 1.0 if successes > 0 else 0.0

        # Overall score (0-100)
        overall = (
            scores["availability"] * 40 +
            (1 - min(scores["latency_ms"] / 2000, 1)) * 30 +
            scores["data_quality"] * 30
        )

        return {
            "service_id": service["id"],
            "service_name": service["name"],
            "scores": scores,
            "overall": round(overall, 1),
            "recommendation": "buy" if overall >= 60 else "skip",
        }
```

### 3. Buyer Agent

Makes purchasing decisions based on quality evaluations:

```python
class BuyerAgent:
    """Makes purchasing decisions within budget constraints."""

    def __init__(self, acf_client, buyer_id, budget):
        self.client = acf_client
        self.buyer_id = buyer_id
        self.budget = budget
        self.spent = 0.0

    async def purchase(self, service, evaluation):
        # Decision logic
        if evaluation["recommendation"] != "buy":
            return {"action": "skipped", "reason": "quality below threshold"}

        if evaluation["overall"] < 60:
            return {"action": "skipped", "reason": f"score {evaluation['overall']} < 60"}

        cost = service["price_per_call"]
        if self.spent + cost > self.budget:
            return {"action": "skipped", "reason": "budget exceeded"}

        # Execute purchase
        r = await self.client.post(
            f"/api/v1/proxy/{service['id']}/",
            json={"full_analysis": True},
            params={"buyer_id": self.buyer_id},
        )

        amount = float(r.headers.get("X-ACF-Amount", "0"))
        self.spent += amount

        return {
            "action": "purchased",
            "service": service["name"],
            "amount": amount,
            "status": r.status_code,
            "data": r.json() if r.status_code < 400 else None,
        }
```

### 4. Reporter Agent

Generates summary reports:

```python
class ReporterAgent:
    """Generates structured reports from swarm activity."""

    def generate_report(self, discoveries, evaluations, purchases):
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "services_discovered": len(discoveries),
                "services_evaluated": len(evaluations),
                "services_purchased": sum(
                    1 for p in purchases if p["action"] == "purchased"
                ),
                "total_spent": sum(
                    p.get("amount", 0) for p in purchases
                ),
            },
            "top_services": sorted(
                evaluations,
                key=lambda e: e["overall"],
                reverse=True,
            )[:5],
            "purchases": purchases,
        }
        return report
```

### 5. Orchestrator

Coordinates all agents:

```python
class SwarmOrchestrator:
    """Coordinates the discovery → evaluate → buy → report pipeline."""

    def __init__(self, config):
        self.client = httpx.AsyncClient(base_url=config["acf_url"])
        self.discovery = DiscoveryAgent(self.client, config["criteria"])
        self.quality = QualityAgent(self.client, config["buyer_id"])
        self.buyer = BuyerAgent(
            self.client, config["buyer_id"], config["budget"]
        )
        self.reporter = ReporterAgent()

    async def run(self):
        # Phase 1: Discover
        print("Phase 1: Discovering services...")
        services = await self.discovery.discover()
        print(f"  Found {len(services)} services")

        # Phase 2: Evaluate (parallel)
        print("Phase 2: Evaluating quality...")
        evaluations = []
        for svc in services:
            eval_result = await self.quality.evaluate(svc)
            evaluations.append(eval_result)
            print(f"  {svc['name']}: {eval_result['overall']}/100")

        # Phase 3: Buy (top candidates)
        print("Phase 3: Purchasing...")
        recommended = [
            (svc, ev) for svc, ev in zip(services, evaluations)
            if ev["recommendation"] == "buy"
        ]
        recommended.sort(key=lambda x: x[1]["overall"], reverse=True)

        purchases = []
        for svc, ev in recommended:
            result = await self.buyer.purchase(svc, ev)
            purchases.append(result)
            print(f"  {svc['name']}: {result['action']}")

        # Phase 4: Report
        print("Phase 4: Generating report...")
        report = self.reporter.generate_report(
            services, evaluations, purchases
        )

        return report
```

## Running the Swarm

```yaml
# config.yaml
acf_url: "https://agentictrade.io"
buyer_id: "swarm-agent"
budget: 5.00

criteria:
  - query: "crypto"
    category: "data"
    max_price: 0.10
  - query: "sentiment"
    max_price: 0.05
```

```bash
python templates/multi-agent-swarm/swarm.py --config config.yaml
```

Output:
```
Phase 1: Discovering services...
  Found 4 services
Phase 2: Evaluating quality...
  CoinSifter Scanner: 85.3/100
  Crypto Sentiment API: 72.1/100
  Token Risk Checker: 68.4/100
  Price Feed: 91.0/100
Phase 3: Purchasing...
  Price Feed: purchased ($0.02)
  CoinSifter Scanner: purchased ($0.05)
  Crypto Sentiment API: purchased ($0.05)
  Token Risk Checker: purchased ($0.10)
Phase 4: Generating report...

Report saved: reports/swarm_2026-03-20.json
Total spent: $0.22 / $5.00 budget
```

## Advanced Patterns

### Continuous Monitoring

Run the swarm on a schedule to continuously discover and evaluate:

```python
async def continuous_swarm(config, interval_hours=6):
    orchestrator = SwarmOrchestrator(config)
    while True:
        report = await orchestrator.run()
        save_report(report)
        await asyncio.sleep(interval_hours * 3600)
```

### Competitive Evaluation

Compare multiple services for the same task:

```python
async def compare_services(services, test_input):
    results = []
    for svc in services:
        start = time.monotonic()
        response = await call_service(svc, test_input)
        latency = time.monotonic() - start

        results.append({
            "service": svc["name"],
            "price": svc["price_per_call"],
            "latency": latency,
            "quality": assess_quality(response),
            "value_score": assess_quality(response) / svc["price_per_call"],
        })

    return sorted(results, key=lambda r: r["value_score"], reverse=True)
```

### Budget Rebalancing

Dynamically shift budget based on service performance:

```python
def rebalance_budget(evaluations, total_budget):
    """Allocate more budget to higher-quality services."""
    total_score = sum(e["overall"] for e in evaluations)
    allocations = {}
    for ev in evaluations:
        weight = ev["overall"] / total_score if total_score > 0 else 0
        allocations[ev["service_id"]] = total_budget * weight
    return allocations
```

## Exercise: Build Your Own Swarm

1. Start with the provided swarm template
2. Add a new agent role (e.g., "Negotiator" that finds cheaper alternatives)
3. Implement parallel evaluation (evaluate multiple services concurrently)
4. Add budget rebalancing based on historical performance
5. Schedule the swarm to run every 6 hours

## Checkpoint

- [ ] Understand the 5-agent swarm architecture
- [ ] Can run the swarm against your marketplace
- [ ] Know how to add custom agent roles
- [ ] Understand budget management in swarms

---

*Next: [Chapter 10 — Production Deployment →](./10-deployment.md)*
