# Chapter 4: Service Registration & Discovery

## Registering Services

A "service" in ACF is any HTTP API that an agent can call. Registration tells the marketplace:
- What the service does (description, category)
- Where to reach it (base_url)
- How much it costs (price_per_call, free_tier_calls)
- Who gets paid (seller_id)

### Basic Registration

```python
import httpx

client = httpx.Client(base_url="https://agentictrade.io")

# Register a sentiment analysis API
response = client.post("/api/v1/services", json={
    "name": "Crypto Sentiment Analyzer",
    "description": "Real-time sentiment scoring for any cryptocurrency. "
                   "Returns score (-1.0 to 1.0), confidence, and top sources.",
    "base_url": "https://your-api.com/v1",
    "price_per_call": 0.05,
    "free_tier_calls": 10,
    "category": "crypto",
    "seller_id": "your-seller-id",
})

service = response.json()
print(f"Registered: {service['id']}")
```

### Bulk Registration from YAML

For registering multiple services, use the API Monetization template:

```yaml
# config.yaml
services:
  - name: "Crypto Sentiment Analyzer"
    description: "Real-time sentiment scoring"
    endpoint: "https://your-api.com/v1"
    price: 0.05
    free_calls: 10
    category: "crypto"

  - name: "Token Risk Scanner"
    description: "Smart contract security analysis"
    endpoint: "https://your-api.com/v1/scan"
    price: 0.10
    free_calls: 3
    category: "crypto"
```

```bash
python templates/api-monetization/register_services.py --config config.yaml
```

### Service Lifecycle

```
Draft → Active → Paused → Archived
  │                │
  └── rejected     └── re-activated
```

Update service status:

```python
# Pause a service (stops accepting new calls)
client.patch(f"/api/v1/services/{service_id}", json={
    "status": "paused"
})

# Re-activate
client.patch(f"/api/v1/services/{service_id}", json={
    "status": "active"
})
```

## Discovery API

Buyer agents need to find services. ACF provides search with filtering:

### Search by Query

```python
# Text search across service names and descriptions
results = client.get("/api/v1/services", params={
    "q": "sentiment analysis"
}).json()
```

### Filter by Category

```python
results = client.get("/api/v1/services", params={
    "category": "crypto"
}).json()
```

### Filter by Price Range

```python
results = client.get("/api/v1/services", params={
    "max_price": 0.10,
    "min_free_tier": 5
}).json()
```

### Combined Filters

```python
results = client.get("/api/v1/services", params={
    "q": "crypto",
    "category": "data",
    "max_price": 0.05,
    "status": "active",
}).json()
```

## Writing Good Service Descriptions

Your service description is how buyer agents (and LLMs) decide whether to purchase. Write for machines, not just humans:

### Bad Description
```
"A sentiment analysis tool"
```

### Good Description
```
"Real-time cryptocurrency sentiment scoring. Accepts a ticker symbol (e.g., BTC, ETH)
and returns: sentiment_score (-1.0 bearish to 1.0 bullish), confidence (0-100%),
source_count (number of sources analyzed), and top_sources (list of URLs).
Covers 500+ cryptocurrencies. Data refreshed every 5 minutes from Twitter, Reddit,
and news feeds. Response time: <500ms."
```

The good description tells an LLM agent:
- **Input format** (ticker symbol)
- **Output format** (score, confidence, sources)
- **Coverage** (500+ cryptos)
- **Freshness** (5-minute refresh)
- **Performance** (500ms response)

## Pricing Strategies

### Per-Call Pricing

Best for stateless queries:

```json
{
  "price_per_call": 0.05,
  "free_tier_calls": 10
}
```

### Tiered Free Tiers

Give generous free tiers for discovery, charge for production use:

| Tier | Free Calls | Price After |
|------|-----------|-------------|
| Hobby | 100/month | $0.05 |
| Startup | 1,000/month | $0.03 |
| Enterprise | Custom | Custom |

### Value-Based Pricing

Price based on the value delivered:

```
Simple query (lookup)       → $0.01
Analysis (sentiment)        → $0.05
Complex report (multi-step) → $0.25
```

## Exercise: Register Your First Service

1. Pick any public API (https://httpbin.org works for testing)
2. Register it with appropriate pricing
3. Use the discovery API to search for it
4. Make 5 free tier calls through the proxy
5. Make 1 paid call and verify the charge

```bash
# Hint: Use the smoke test CLI to verify
python cli/acf_test_payment.py --url https://agentictrade.io
```

## Checkpoint

- [ ] Registered at least one service
- [ ] Can search services by query and filters
- [ ] Understand free tier mechanics
- [ ] Service descriptions are LLM-friendly

---

*Next: [Chapter 5 — Billing & Credits →](./05-billing.md)*
