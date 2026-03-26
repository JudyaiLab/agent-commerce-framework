# Chapter 5: Billing & Credits

## The Pre-Paid Model

ACF uses a pre-paid credit system. Buyer agents deposit funds first, then spend them on API calls. This eliminates credit risk and makes billing instantaneous — no invoices, no payment terms, no collections.

```
Deposit → Balance → Spend → Check
  $10       $10     -$0.05   $9.95
```

## Balance Management

### Check Balance

```python
import httpx

client = httpx.Client(base_url="https://agentictrade.io")

balance = client.get("/api/v1/balance/my-agent").json()
print(f"Balance: ${balance['balance']:.2f}")
```

### Deposit Flow (Test Mode)

For development, use the admin credit endpoint:

```python
# Add $10 test credits
client.post("/api/v1/admin/credit", params={
    "buyer_id": "my-agent",
    "amount": 10.00,
    "admin_key": "test-admin-secret",  # From .env
})
```

### Deposit Flow (Production — Crypto)

In production, buyers deposit via NOWPayments:

```python
# 1. Create deposit request
deposit = client.post("/api/v1/deposits", json={
    "buyer_id": "my-agent",
    "amount": 10.00,
    "currency": "USD",
}).json()

# 2. Buyer pays at the checkout URL
print(f"Pay here: {deposit['checkout_url']}")

# 3. NOWPayments sends IPN callback to ACF
# ACF automatically credits the balance when payment confirms
```

### Deposit Flow (Production — PayPal)

For fiat payments via PayPal:

```python
# 1. Create PayPal checkout session
session = client.post("/api/v1/deposits/paypal", json={
    "buyer_id": "my-agent",
    "amount": 10.00,
}).json()

# 2. Redirect to PayPal checkout
print(f"Pay here: {session['checkout_url']}")

# 3. PayPal webhook → ACF credits balance
```

## How Billing Works Per Call

Every proxy call goes through this billing check:

```python
def bill_proxy_call(service, buyer_id):
    """Called by the proxy before routing to seller."""

    # Count how many calls this buyer has made to this service
    usage_count = db.count_usage(service.id, buyer_id)

    # Free tier check
    if usage_count < service.free_tier_calls:
        return BillResult(amount=0.0, free_tier=True)

    # Balance check
    balance = db.get_balance(buyer_id)
    if balance < service.price_per_call:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "error": "insufficient_balance",
                "balance": balance,
                "required": service.price_per_call,
            }
        )

    # Deduct
    new_balance = db.deduct_balance(buyer_id, service.price_per_call)

    # Credit seller (minus platform fee)
    seller_amount = service.price_per_call * (1 - PLATFORM_FEE_PCT)
    db.credit_seller(service.seller_id, seller_amount)

    return BillResult(amount=service.price_per_call, free_tier=False)
```

### Response Headers

Every proxy response includes billing information:

```
X-ACF-Free-Tier: false
X-ACF-Amount: 0.05
X-ACF-Balance: 9.95
X-ACF-Service: svc_abc123
```

Agents can use these headers to track spending in real-time.

## Budget Management for Agents

Smart agents should manage their budgets. Here's a pattern:

```python
class BudgetAwareAgent:
    def __init__(self, acf_url, buyer_id, budget_limit=10.0):
        self.client = httpx.Client(base_url=acf_url)
        self.buyer_id = buyer_id
        self.budget_limit = budget_limit
        self.spent = 0.0

    def check_budget(self, cost):
        """Check if we can afford this call."""
        if self.spent + cost > self.budget_limit:
            raise BudgetExceeded(
                f"Budget limit ${self.budget_limit} would be exceeded. "
                f"Spent: ${self.spent:.2f}, Cost: ${cost:.2f}"
            )

    def call_service(self, service_id, path, data):
        """Make a service call with budget tracking."""
        # Get service price first
        svc = self.client.get(f"/api/v1/services/{service_id}").json()
        self.check_budget(svc["price_per_call"])

        # Make the call
        r = self.client.post(
            f"/api/v1/proxy/{service_id}/{path}",
            json=data,
            params={"buyer_id": self.buyer_id},
        )

        # Track actual spend from headers
        amount = float(r.headers.get("X-ACF-Amount", "0"))
        self.spent += amount

        return r.json()
```

## Settlement: Paying Sellers

ACF accumulates seller earnings and pays out periodically:

```python
# Check seller's pending balance
seller_status = client.get(
    "/api/v1/settlement/status/my-seller-id"
).json()
print(f"Pending: ${seller_status['pending']:.2f}")
print(f"Total earned: ${seller_status['total_earned']:.2f}")
```

### Settlement Triggers

- **Manual**: Admin triggers payout via API
- **Threshold**: Automatic when pending balance exceeds a threshold
- **Scheduled**: Periodic (daily/weekly) settlement runs

```bash
# Trigger manual settlement
curl -X POST "https://agentictrade.io/api/v1/settlement/run?admin_key=test-admin-secret"
```

## Exercise: Build a Budget Tracker

1. Create a buyer agent with a $5 budget
2. Register a service priced at $0.10/call
3. Make calls until you hit 402 (Payment Required)
4. Track spending via response headers
5. Implement a budget warning at 80% utilization

## Checkpoint

- [ ] Understand pre-paid credit model
- [ ] Can create deposits (test mode and production)
- [ ] Understand per-call billing flow
- [ ] Can read billing headers from proxy responses
- [ ] Understand settlement flow for sellers

---

*Next: [Chapter 6 — The Proxy: SSRF Protection & Routing →](./06-proxy.md)*
