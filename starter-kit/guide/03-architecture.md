# Chapter 3: Architecture Deep Dive

## System Architecture

The Agent Commerce Framework is a FastAPI application with six core modules:

```
api/
├── main.py              # App entry point, middleware, CORS
├── routes/
│   ├── services.py      # Service registry CRUD
│   ├── billing.py       # Balance, deposits, IPN callbacks
│   ├── settlement.py    # Seller payouts
│   ├── auth.py          # API key management
│   ├── discovery.py     # Search and recommendations
│   ├── identity.py      # Agent identity (DID/VC)
│   ├── reputation.py    # Quality scoring
│   └── health.py        # Health check + landing page
marketplace/
├── db.py                # SQLite connection + schema
├── models.py            # Pydantic models
├── proxy.py             # SSRF-hardened HTTP proxy
├── registry.py          # Service registration logic
├── settlement.py        # Payout calculation
├── discovery.py         # Search engine
├── identity.py          # Identity verification
├── reputation.py        # Reputation scoring
└── payment.py           # Payment provider abstraction
```

## Database Schema

ACF uses SQLite with 7 core tables:

```sql
-- Services available for purchase
CREATE TABLE services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    base_url TEXT NOT NULL,
    price_per_call REAL DEFAULT 0.0,
    free_tier_calls INTEGER DEFAULT 0,
    category TEXT,
    seller_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Buyer credit balances
CREATE TABLE balances (
    buyer_id TEXT PRIMARY KEY,
    balance REAL DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Every API proxy call logged
CREATE TABLE usage_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id TEXT NOT NULL,
    buyer_id TEXT NOT NULL,
    amount REAL DEFAULT 0.0,
    free_tier BOOLEAN DEFAULT 0,
    status_code INTEGER,
    response_time_ms REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crypto deposit tracking
CREATE TABLE deposits (
    id TEXT PRIMARY KEY,
    buyer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    provider TEXT,
    status TEXT DEFAULT 'pending',
    external_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- API keys for authentication
CREATE TABLE api_keys (
    key_id TEXT PRIMARY KEY,
    secret_hash TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    permissions TEXT DEFAULT 'read,buy',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seller pending balances
CREATE TABLE seller_balances (
    seller_id TEXT PRIMARY KEY,
    pending REAL DEFAULT 0.0,
    total_earned REAL DEFAULT 0.0,
    last_settlement TIMESTAMP
);

-- Agent identities
CREATE TABLE agent_identities (
    agent_id TEXT PRIMARY KEY,
    display_name TEXT,
    did TEXT,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## The Proxy: How Agent-to-Agent Calls Work

The proxy is the most critical component. It sits between buyer and seller, handling:

1. **Authentication** — Is the buyer authorized?
2. **Balance check** — Can the buyer afford this call?
3. **Free tier tracking** — Has the buyer exhausted free calls?
4. **SSRF protection** — Is the target URL safe?
5. **Request routing** — Forward to seller's API
6. **Billing** — Deduct from buyer, credit seller
7. **Logging** — Record usage for analytics

### SSRF Protection

Without protection, a malicious service registration could point `base_url` at internal services:

```json
{
  "name": "Totally Legit Service",
  "base_url": "http://169.254.169.254"  // AWS metadata!
}
```

ACF prevents this by:

```python
BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / cloud metadata
    ipaddress.ip_network("::1/128"),
]
```

Every `base_url` is resolved to an IP and checked against blocked ranges before the request is sent.

### Billing Flow

```python
# Simplified billing logic (actual code in marketplace/proxy.py)

def process_proxy_call(service, buyer_id, path, body):
    # 1. Check balance
    balance = get_balance(buyer_id)
    if balance <= 0 and not has_free_tier(service, buyer_id):
        raise InsufficientFunds()

    # 2. Check free tier
    usage_count = count_usage(service.id, buyer_id)
    is_free = usage_count < service.free_tier_calls

    # 3. Route request (SSRF-safe)
    response = safe_proxy(service.base_url, path, body)

    # 4. Bill
    if not is_free:
        amount = service.price_per_call
        deduct_balance(buyer_id, amount)
        credit_seller(service.seller_id, amount * (1 - PLATFORM_FEE))

    # 5. Log
    log_usage(service.id, buyer_id, amount, is_free)

    return response
```

## Payment Provider Architecture

ACF supports three payment providers through a unified interface:

```python
class PaymentProvider(ABC):
    @abstractmethod
    def create_payment(self, amount: float, buyer_id: str) -> PaymentRequest:
        """Create a payment request (deposit URL, invoice, etc.)"""

    @abstractmethod
    def verify_callback(self, request: Request) -> PaymentConfirmation:
        """Verify and process payment provider callback"""
```

### NOWPayments (Crypto)

Best for: accepting crypto deposits (BTC, ETH, USDC, etc.)

```
Buyer → NOWPayments checkout → pays in crypto → IPN callback → ACF credits balance
```

### PayPal (Fiat)

Best for: traditional card payments, enterprise clients

```
Buyer → PayPal checkout → pays with card → webhook → ACF credits balance
```

### x402 + AgentKit (On-Chain USDC)

Best for: fully autonomous agent-to-agent payments on Base network

```
Agent → creates USDC transaction → sends via x402 header → ACF verifies on-chain → credits balance
```

## Configuration

All configuration is via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./marketplace.db` | SQLite file location |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `PLATFORM_FEE_PCT` | `0.10` | Platform fee (10%) |
| `ACF_ADMIN_SECRET` | `test-admin-secret` | Admin API key |
| `NOWPAYMENTS_API_KEY` | — | NOWPayments API key |
| `NOWPAYMENTS_IPN_SECRET` | — | IPN HMAC secret |
| `PAYPAL_CLIENT_ID` | — | PayPal client ID |
| `WALLET_ADDRESS` | — | USDC wallet (Base) |
| `CDP_API_KEY_NAME` | — | Coinbase Dev Platform key |
| `CDP_API_KEY_PRIVATE` | — | CDP private key |

## Extension Points

The framework is designed to be extended:

### Custom Payment Provider

```python
from marketplace.payment import PaymentProvider

class MyProvider(PaymentProvider):
    def create_payment(self, amount, buyer_id):
        # Your payment logic
        ...

    def verify_callback(self, request):
        # Your verification logic
        ...
```

### Custom Middleware

```python
# Add to api/main.py
@app.middleware("http")
async def custom_middleware(request, call_next):
    # Rate limiting, logging, custom auth, etc.
    response = await call_next(request)
    return response
```

### Custom Discovery

Override the default search with your own ranking algorithm:

```python
from marketplace.discovery import DiscoveryEngine

class MyDiscovery(DiscoveryEngine):
    def search(self, query, filters):
        # Custom ranking, ML-based recommendations, etc.
        ...
```

## Checkpoint

You should now understand:

- [ ] The 6 core modules and their responsibilities
- [ ] How the proxy routes and bills agent-to-agent calls
- [ ] SSRF protection mechanisms
- [ ] The three payment provider options
- [ ] How to extend the framework

---

*Next: [Chapter 4 — Service Registration & Discovery →](./04-services.md)*
