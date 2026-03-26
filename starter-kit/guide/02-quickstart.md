# Chapter 2: Quick Start — Your First Agent Transaction

## Goal

By the end of this chapter, you'll have:
- Connected to the AgenticTrade marketplace
- Discovered available services
- Made your first API call through the marketplace proxy
- Understood the billing flow

Total time: ~10 minutes.

## Step 1: Get Your API Key

Sign up at [agentictrade.io](https://agentictrade.io) and create an API key:

```bash
# Create a buyer API key
curl -X POST https://agentictrade.io/api/v1/keys \
  -H "Content-Type: application/json" \
  -d '{
    "owner_id": "my-first-agent",
    "role": "buyer"
  }'
```

Response:
```json
{
  "key_id": "k_abc123...",
  "secret": "sec_xyz789...",
  "role": "buyer",
  "message": "Save your secret — it won't be shown again"
}
```

Save the key:
```bash
export ACF_API_KEY="k_abc123:sec_xyz789"  # key_id:secret format
```

## Step 2: Verify Connection

```bash
# Health check — no auth needed
curl https://agentictrade.io/health
# {"status":"ok","version":"0.6.0","services":4}
```

Run the smoke test:
```bash
python cli/acf_test_payment.py --api-key $ACF_API_KEY
```

## Step 3: Discover Services

Browse what's available on the marketplace:

```bash
curl https://agentictrade.io/api/v1/discover \
  -H "Authorization: Bearer $ACF_API_KEY"
```

Response:
```json
{
  "services": [
    {
      "id": "svc_...",
      "name": "CoinSifter Scanner",
      "price_per_call": "0.50",
      "free_tier_calls": 0,
      "category": "crypto"
    },
    {
      "id": "svc_...",
      "name": "CoinSifter Demo",
      "price_per_call": "0.00",
      "free_tier_calls": 100,
      "category": "crypto"
    }
  ]
}
```

Save a service ID for testing:
```bash
export SERVICE_ID="svc_..."  # Replace with an actual service ID
```

## Step 4: Call a Service

Call the service through the marketplace proxy:

```bash
curl https://agentictrade.io/api/v1/proxy/$SERVICE_ID/ \
  -H "Authorization: Bearer $ACF_API_KEY"
```

The marketplace handles everything:
- Authentication and rate limiting
- Billing (free tier tracking or balance deduction)
- SSRF-safe proxying to the service provider
- Usage logging

Check the response headers for billing info:
```
X-ACF-Free-Tier: true         # Using free tier
X-ACF-Amount: 0.00            # No charge
X-ACF-Balance: 5.00           # Current balance
```

## Step 5: Use the Python SDK

The SDK handles authentication and API calls for you:

```python
from sdk.client import ACFClient

client = ACFClient(api_key="your_key_id:your_secret")

# Discover services
services = client.search(query="crypto")
print(f"Found {len(services.get('services', []))} services")

# Call a service
result = client.call_service(
    service_id="svc_...",
    method="GET",
    path="/",
)
print(result)
```

For automated payment handling with x402 (on-chain USDC):

```python
from sdk.buyer import BuyerAgent

async with BuyerAgent(
    api_key="your_key_id:your_secret",
    cdp_api_key_id="...",       # From Coinbase Developer Platform
    cdp_api_key_secret="...",
) as buyer:
    # Payment is handled automatically
    result = await buyer.call_service("svc_...", path="/forecast")
    print(result)
```

## What Just Happened?

The complete flow:

```
1. You created an API key → identity on the marketplace
2. You discovered services → browsed available APIs
3. You called a service → marketplace proxied your request:
   a. Verified your API key ✓
   b. Checked free tier quota or balance ✓
   c. Proxied request to the service provider (SSRF-safe) ✓
   d. Logged usage record ✓
   e. Returned response with billing headers ✓
4. The provider gets paid (after platform fee)
```

## Checkpoint

Before moving on, verify:

- [ ] API key created and working
- [ ] Health check returns `"ok"`
- [ ] Service discovery returns available services
- [ ] Proxy call succeeds
- [ ] You understand the billing flow

All checked? Let's dive into the architecture.

---

*Next: [Chapter 3 — Architecture Deep Dive →](./03-architecture.md)*
