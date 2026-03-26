# Chapter 7: Payment Integration

## Three Payment Rails

ACF supports three payment methods, each suited to different use cases:

| Provider | Currency | Best For | Agent-Native? |
|----------|----------|----------|---------------|
| NOWPayments | Crypto (BTC, ETH, USDC, ...) | Multi-coin deposits | Partial |
| PayPal | Fiat (USD, EUR, ...) | Enterprise, regulated | No |
| x402 + AgentKit | USDC on Base | Fully autonomous agents | Yes |

You can enable one, two, or all three simultaneously.

## Option 1: NOWPayments (Crypto Gateway)

### Setup

1. Create account at [nowpayments.io](https://nowpayments.io)
2. Get API key and IPN secret from dashboard
3. Configure:

```bash
# .env
NOWPAYMENTS_API_KEY=your-api-key
NOWPAYMENTS_IPN_SECRET=your-ipn-secret
```

### How It Works

```
Buyer Agent                ACF Server               NOWPayments
    │                          │                          │
    ├── POST /deposits ───────▶│                          │
    │                          ├── Create invoice ───────▶│
    │   ◀── checkout_url ──────┤                          │
    │                          │                          │
    │   (buyer pays in crypto) │                          │
    │                          │                          │
    │                          │◀── IPN callback ─────────┤
    │                          │   (HMAC-SHA512 verified) │
    │                          │                          │
    │                          ├── Credit balance          │
    │                          │                          │
    ├── GET /balance ─────────▶│                          │
    │   ◀── $10.00 ────────────┤                          │
```

### IPN Callback Verification

ACF verifies NOWPayments callbacks using HMAC-SHA512:

```python
def verify_nowpayments_ipn(body: bytes, signature: str, secret: str) -> bool:
    """Verify NOWPayments IPN signature."""
    # NOWPayments signs the sorted JSON body
    data = json.loads(body)
    sorted_body = json.dumps(data, sort_keys=True).encode()
    expected = hmac.new(
        secret.encode(), sorted_body, hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

### Creating a Deposit

```python
# Python SDK example
import httpx

client = httpx.Client(base_url="https://agentictrade.io")

# Create deposit
deposit = client.post("/api/v1/deposits", json={
    "buyer_id": "my-agent-001",
    "amount": 10.00,
    "currency": "USD",
}).json()

print(f"Deposit ID: {deposit['id']}")
print(f"Pay at: {deposit['checkout_url']}")
print(f"Status: {deposit['status']}")  # "pending"

# After payment confirms (IPN callback):
balance = client.get("/api/v1/balance/my-agent-001").json()
print(f"Balance: ${balance['balance']}")  # 10.00
```

## Option 2: PayPal (Fiat)

### Setup

1. Create account at [developer.paypal.com](https://developer.paypal.com)
2. Get client ID and secret from Dashboard → Apps & Credentials
3. Configure:

```bash
# .env
PAYPAL_CLIENT_ID=your_client_id
PAYPAL_CLIENT_SECRET=your_client_secret
```

### PayPal for Agent Commerce

PayPal is designed for agent-to-agent payments. It extends PayPal's existing infrastructure with:

- **Agent identity** — link payments to specific agents
- **Automated checkout** — no human intervention needed
- **Webhook notifications** — real-time payment status

### Integration

```python
# Create PayPal deposit session
deposit = client.post("/api/v1/deposits/paypal", json={
    "buyer_id": "enterprise-agent",
    "amount": 100.00,
    "success_url": "https://your-app.com/deposit/success",
    "cancel_url": "https://your-app.com/deposit/cancel",
}).json()

# Redirect to PayPal checkout
print(f"Checkout: {deposit['checkout_url']}")
```

### Webhook Handler

ACF automatically handles PayPal webhooks:

```python
# PayPal sends CHECKOUT.ORDER.APPROVED
# ACF verifies signature, credits balance
```

## Option 3: x402 + AgentKit (On-Chain USDC)

This is the most agent-native option. Agents hold their own crypto wallets and pay directly on the Base network.

### Setup

1. Create account at [portal.cdp.coinbase.com](https://portal.cdp.coinbase.com)
2. Generate API key
3. Configure:

```bash
# .env
WALLET_ADDRESS=0x...              # Your USDC receiving address (Base)
CDP_API_KEY_NAME=your-key-name
CDP_API_KEY_PRIVATE=your-private-key
```

### How x402 Works

The x402 protocol adds payment to HTTP. When an agent gets a 402 (Payment Required) response, it can automatically pay:

```
Agent                         ACF Server
  │                              │
  ├── GET /api/v1/proxy/... ────▶│
  │                              │
  │   ◀── 402 Payment Required ──┤
  │       X-Payment-Amount: 0.05 │
  │       X-Payment-Address: 0x. │
  │       X-Payment-Network: base│
  │                              │
  │   (agent creates USDC tx)    │
  │                              │
  ├── GET /api/v1/proxy/... ────▶│
  │   X-Payment-Proof: 0xtxhash │
  │                              │
  │   ◀── 200 OK ────────────────┤
  │       (response data)        │
```

### AgentKit Wallet

Coinbase AgentKit lets agents create and manage their own wallets:

```python
from cdp import Cdp, Wallet

# Initialize CDP client
Cdp.configure(
    api_key_name="your-key-name",
    api_key_private="your-private-key",
)

# Create agent wallet
wallet = Wallet.create(network_id="base-mainnet")
address = wallet.default_address

print(f"Agent wallet: {address}")

# Fund with USDC and make payments
# (see AgentKit docs for full wallet management)
```

## Choosing a Payment Provider

### Decision Matrix

| Factor | NOWPayments | PayPal | x402+AgentKit |
|--------|-------------|--------|---------------|
| Setup time | 30 min | 1 hour | 2 hours |
| KYC required | Minimal | Full | None |
| Agent autonomy | Medium | Low | Full |
| Currencies | 300+ crypto | Fiat | USDC |
| Transaction fee | 0.5-1% | 2.9% + $0.30 | Gas only (~$0.01) |
| Settlement speed | 1-6 confirms | 2-7 days | Instant |
| Best for | Crypto-native users | Enterprise | Autonomous agents |

### Recommended Approach

Start with **NOWPayments** for quick setup, then add **x402+AgentKit** for fully autonomous agents. Use **PayPal** when you need enterprise/fiat support.

```python
# You can enable multiple providers simultaneously
# .env
NOWPAYMENTS_API_KEY=...     # Crypto deposits
PAYPAL_CLIENT_ID=...        # Fiat deposits
WALLET_ADDRESS=...          # x402 on-chain
```

## Testing Payments

### Test Mode (No Real Money)

```bash
# Admin credit — instant test balance
curl -X POST "https://agentictrade.io/api/v1/admin/credit?buyer_id=test&amount=100&admin_key=test-admin-secret"
```

### NOWPayments Sandbox

NOWPayments offers a sandbox environment:
```bash
# Use sandbox API key
NOWPAYMENTS_API_KEY=sandbox-key
```

### PayPal Sandbox Mode

PayPal provides sandbox credentials:
```bash
PAYPAL_CLIENT_ID=sandbox_client_id
PAYPAL_CLIENT_SECRET=sandbox_client_secret
# Use PayPal sandbox test accounts
```

## Exercise: Enable Payment Processing

1. Sign up for NOWPayments (free)
2. Add your API key to `.env`
3. Create a deposit request
4. Simulate an IPN callback
5. Verify the balance was credited

```bash
# Run the full payment smoke test
python cli/acf_test_payment.py --url https://agentictrade.io
```

## Checkpoint

- [ ] Understand all three payment options
- [ ] Can create deposit requests
- [ ] Understand IPN/webhook verification
- [ ] Know the trade-offs between providers
- [ ] Tested payment flow (at least test mode)

---

*Next: [Chapter 8 — MCP Server: Let LLMs Buy Services →](./08-mcp.md)*
