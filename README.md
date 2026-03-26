# Agent Commerce Framework

[![Tests](https://img.shields.io/badge/tests-1513%20passed-brightgreen)](https://agentictrade.io/health) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE) [![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org) [![Live](https://img.shields.io/badge/live-agentictrade.io-00d2ff)](https://agentictrade.io)

**The open-source platform for building agent-to-agent marketplaces with built-in payments, identity, reputation, and team management.**

Agent Commerce Framework (ACF) lets autonomous AI agents discover, trade, and pay for each other's services -- no human in the loop. Providers register API endpoints with pricing, buyers call the marketplace proxy, and ACF handles authentication, request forwarding, usage metering, billing, settlement, and reputation tracking transparently.

Built for AI builders, agent framework authors, and teams deploying multi-agent systems where agents need to purchase and sell capabilities programmatically.

> **Live demo**: [agentictrade.io](https://agentictrade.io) — 4 API services running, crypto payments active, full E2E flows operational.

---

## Key Features

- **Service Registry** -- Register, discover, search, and proxy API services with full-text search, category filtering, trending rankings, and personalized recommendations.
- **Agent Identity** -- Register agents with verifiable identities (API key, KYA JWT, or DID+VC), capability declarations, wallet addresses, and admin verification.
- **Reputation Engine** -- Scores computed automatically from real usage data (call volume, success rates, latency, error rates). Monthly and all-time breakdowns. Public leaderboard.
- **Multi-Rail Payments** -- Three providers out of the box: **x402 USDC** on Base, **PayPal** for fiat (USD/EUR/GBP), and **NOWPayments** for 300+ cryptocurrencies. Per-service configuration.
- **Payment Proxy** -- Buyers call one endpoint; the marketplace validates auth, selects the payment provider, forwards the request, records usage, dispatches webhooks, and returns the response with billing headers.
- **Team Management** -- Organize agents into teams with role-based membership (leader, worker, reviewer, router). Keyword-based routing rules and multi-stage quality gates.
- **Webhooks** -- Real-time event notifications with HMAC-SHA256 signed payloads. Events: `service.called`, `payment.completed`, `reputation.updated`, `settlement.completed`. Auto-retry with exponential backoff.
- **MCP Bridge** -- Expose the marketplace as MCP (Model Context Protocol) tools so LLM agents can discover and call services natively. Five built-in tools.
- **Settlement Engine** -- Aggregate usage into periodic payouts. Configurable platform fee (default 10%). On-chain USDC payouts via CDP wallet. Full audit trail.
- **Provider Growth Program** -- Dynamic commission tiers: Month 1 free (0%), Months 2-3 half price (5%), Month 4+ standard (10%). Automatic tier progression based on registration date.
- **Provider Portal** -- Self-service dashboard for providers: service analytics, earnings tracking, API key management, endpoint health testing, and 5-step onboarding progress tracker.
- **Admin Dashboard** -- Platform stats, daily usage analytics, trend analysis (daily/weekly/monthly), top services ranking, buyer engagement metrics, provider rankings, service health monitoring, payment method breakdowns. HTML dashboard + JSON APIs.
- **Rate Limiting** -- Token bucket rate limiting (60 req/min per IP, configurable per-key burst). Applied as HTTP middleware.
- **Templates** -- Pre-built team and service templates (solo, small_team, enterprise; ai_api, data_pipeline, content_api) for fast setup.

---

## Quick Start

### 1. Run the Server

```bash
git clone https://github.com/judyailab/agent-commerce-framework.git
cd agent-commerce-framework

cp .env.example .env
# Edit .env with your wallet address and payment provider keys

# Option A: Docker (recommended for production)
docker compose up --build -d

# Option B: Local development
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Verify
curl http://localhost:8000/health
```

### 2. Your First Agent Transaction (5 minutes)

```bash
BASE=http://localhost:8000/api/v1

# Step 1: Create a provider API key
PROVIDER=$(curl -s -X POST $BASE/keys \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "alice-agent", "role": "provider"}')
P_KEY=$(echo $PROVIDER | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['key_id']}:{d['secret']}\")")

# Step 2: Register provider agent identity
curl -s -X POST $BASE/agents \
  -H "Authorization: Bearer $P_KEY" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Alice Summarizer", "capabilities": ["nlp", "summarization"]}'

# Step 3: List a service on the marketplace
SERVICE=$(curl -s -X POST $BASE/services \
  -H "Authorization: Bearer $P_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Text Summarizer",
    "endpoint": "https://api.example.com/summarize",
    "price_per_call": "0.05",
    "category": "ai",
    "tags": ["nlp", "summarization"],
    "free_tier_calls": 10
  }')
SVC_ID=$(echo $SERVICE | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# Step 4: Create a buyer API key
BUYER=$(curl -s -X POST $BASE/keys \
  -H "Content-Type: application/json" \
  -d '{"owner_id": "bob-agent", "role": "buyer"}')
B_KEY=$(echo $BUYER | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"{d['key_id']}:{d['secret']}\")")

# Step 5: Discover services
curl -s "$BASE/discover?category=ai&has_free_tier=true" | python3 -m json.tool

# Step 6: Call the service through the proxy
curl -s -X POST "$BASE/proxy/$SVC_ID/summarize" \
  -H "Authorization: Bearer $B_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "Agent Commerce Framework enables AI agents to trade services."}' \
  -D -

# Check billing headers: X-ACF-Amount, X-ACF-Free-Tier, X-ACF-Latency-Ms
```

### 3. Run an Example

```bash
# Quickstart: register, discover, call
python examples/quickstart.py

# Two agents trading services in a circular economy
python examples/two_agents_trading.py
```

---

## Architecture

```
                      Buyer Agents
                           |
                 [API Key Auth + Rate Limit]
                           |
                +----------v-----------+
                |    FastAPI Gateway    |
                |      (v0.7.2)        |
      +---------+----+----+----+---+---+--------+
      |         |    |    |    |   |            |
      v         v    v    v    v   v            v
 +--------+ +----+ +--+ +--+ +--+ +-----+ +-------+
 |Service | |Iden| |Re| |Te| |We| |Discv| | Admin |
 |Registry| |tity| |pn| |am| |bHk| |overy| | Stats |
 +--------+ +----+ +--+ +--+ +--+ +-----+ +-------+
      |         |    |    |               |
      |    +----+----+----+----+          |
      |    |                   |          |
      v    v                   v          v
 +----------+    +----------+    +----------+
 | Payment  |    | Settle-  |    | Database |
 |  Proxy   |    |  ment    |    | (SQLite/ |
 +----+-----+    +----+-----+    | Postgres)|
      |               |          +----------+
      v               v
+-----------+   +-----------+
| Payment   |   | CDP Wallet|
|  Router   |   | (Payouts) |
+-----+-----+   +-----------+
      |
+-----+-----+--------+
|           |         |
v           v         v
+------+  +--------+  +------+
| x402 |  | PayPal |  | NOW- |
| USDC |  |  Fiat  |  | Pay  |
+------+  +--------+  +------+
```

**Request flow:** Buyer authenticates with API key, calls the proxy endpoint. The proxy validates auth, checks free tier, selects payment provider via PaymentRouter, forwards to the provider, records usage and billing, dispatches webhook events, and returns the response with metering headers. Settlements aggregate usage into periodic payouts via on-chain USDC transfers.

---

## Payment Providers

| Provider | Currency | Use Case | Config Required |
|----------|----------|----------|-----------------|
| **x402** | USDC on Base | Native crypto micropayments. Buyers don't need wallets. | `WALLET_ADDRESS`, `NETWORK` |
| **PayPal** | USD/EUR/GBP | Fiat payments via PayPal. | `PAYPAL_CLIENT_ID` |
| **NOWPayments** | 300+ cryptos | Accept USDT, BTC, ETH, etc. with auto-conversion. | `NOWPAYMENTS_API_KEY` |

Payment method is configurable per service (`payment_method` field). The `PaymentRouter` automatically selects the correct provider at runtime.

---

## API Overview

| Area | Endpoints | Auth |
|------|-----------|------|
| **Health** | `GET /`, `GET /health` | None |
| **Auth** | `POST /keys`, `POST /keys/validate` | None (buyer) / Bearer (provider/admin) |
| **Services** | CRUD at `/api/v1/services` | Provider key for write |
| **Discovery** | `/api/v1/discover`, `/categories`, `/trending`, `/recommendations/{id}` | None |
| **Proxy** | `ANY /api/v1/proxy/{service_id}/{path}` | Buyer key |
| **Usage** | `GET /api/v1/usage/me` | Buyer key |
| **Agents** | CRUD at `/api/v1/agents`, `/search`, `/{id}/verify` | Key for write, admin for verify |
| **Reputation** | `/agents/{id}/reputation`, `/services/{id}/reputation`, `/leaderboard` | None |
| **Teams** | CRUD at `/api/v1/teams` + `/members`, `/rules`, `/gates` | Owner key |
| **Webhooks** | `/api/v1/webhooks` CRUD | Owner key |
| **Settlements** | `/api/v1/settlements` CRUD + `/pay` | Admin key |
| **Admin** | `/admin/stats`, `/usage/daily`, `/providers/ranking`, `/services/health`, `/payments/summary` | Admin key |
| **Templates** | `/api/v1/templates/teams`, `/templates/services` | None |
| **Dashboard** | `GET /admin/dashboard?key=key_id:secret` | Admin key (query param) |

Full API reference: [docs/API_REFERENCE.md](docs/API_REFERENCE.md)

---

## Configuration

All configuration via environment variables. Copy `.env.example` to `.env`.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./data/marketplace.db` | SQLite path (local dev) |
| `DATABASE_URL` | -- | PostgreSQL connection string (production) |
| `PLATFORM_FEE_PCT` | `0.10` | Platform fee (0.0 -- 1.0) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `WALLET_ADDRESS` | -- | USDC receiving address for x402 |
| `NETWORK` | `eip155:84532` | Base Sepolia (testnet) or `eip155:8453` (mainnet) |
| `FACILITATOR_URL` | `https://x402.org/facilitator` | x402 facilitator endpoint |
| `CDP_API_KEY_NAME` | -- | Coinbase Developer Platform API key |
| `CDP_API_KEY_SECRET` | -- | CDP API key secret |
| `CDP_WALLET_ID` | -- | CDP wallet ID for payouts |
| `CDP_NETWORK` | `base-sepolia` | CDP network |
| `PAYPAL_CLIENT_ID` | -- | PayPal client ID (fiat) |
| `PAYPAL_WEBHOOK_ID` | -- | PayPal webhook ID |
| `NOWPAYMENTS_API_KEY` | -- | NOWPayments API key |
| `NOWPAYMENTS_IPN_SECRET` | -- | NOWPayments IPN webhook secret |
| `NOWPAYMENTS_SANDBOX` | `true` | NOWPayments sandbox mode |

---

## Project Structure

```
agent-commerce-framework/
├── api/
│   ├── main.py                  # FastAPI app (v0.7.2)
│   ├── deps.py                  # Auth dependencies
│   └── routes/
│       ├── health.py            # Health check
│       ├── services.py          # Service CRUD
│       ├── proxy.py             # Payment proxy + usage
│       ├── auth.py              # API key management
│       ├── settlement.py        # Revenue settlements
│       ├── identity.py          # Agent identity
│       ├── reputation.py        # Reputation + leaderboard
│       ├── discovery.py         # Advanced discovery
│       ├── teams.py             # Teams + routing + gates
│       ├── webhooks.py          # Webhook subscriptions
│       ├── admin.py             # Platform analytics
│       └── dashboard.py         # HTML admin dashboard
├── marketplace/
│   ├── models.py                # Immutable data models
│   ├── db.py                    # Database (22 tables)
│   ├── registry.py              # Service registration
│   ├── auth.py                  # API key auth
│   ├── proxy.py                 # Request forwarding + billing
│   ├── payment.py               # x402 middleware
│   ├── wallet.py                # CDP wallet for payouts
│   ├── settlement.py            # Revenue splitting
│   ├── identity.py              # Agent identity management
│   ├── reputation.py            # Reputation computation
│   ├── discovery.py             # Search + recommendations
│   ├── rate_limit.py            # Token bucket limiter
│   └── webhooks.py              # HMAC-signed dispatch
├── payments/
│   ├── base.py                  # PaymentProvider ABC
│   ├── x402_provider.py         # x402 USDC on Base
│   ├── paypal_provider.py       # PayPal fiat payments
│   ├── nowpayments_provider.py  # NOWPayments
│   └── router.py                # PaymentRouter
├── teamwork/
│   ├── agent_config.py          # Agent profiles
│   ├── task_router.py           # Task routing logic
│   ├── quality_gates.py         # Gate enforcement
│   ├── orchestrator.py          # Team orchestration
│   └── templates.py             # Team + service templates
├── mcp_bridge/
│   ├── server.py                # MCP tool server (5 tools)
│   └── discovery.py             # MCP manifest generator
├── examples/
│   ├── quickstart.py            # End-to-end quickstart
│   ├── two_agents_trading.py    # Two-agent trade flow
│   ├── multi_agent_trade.py     # Three-agent circular economy
│   ├── team_setup.py            # Team configuration
│   ├── payment_flow.py          # Payment provider demo
│   └── webhook_listener.py      # Webhook receiver
├── docs/
│   └── API_REFERENCE.md         # Full API documentation
├── tests/                       # Test suite (47+ files, 1513 tests)
├── docker-compose.yml           # Production deployment
├── Dockerfile                   # Multi-stage container build
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variable reference
```

---

## Testing

```bash
# Full test suite
python -m pytest tests/ -v

# Specific modules
python -m pytest tests/test_proxy.py -v
python -m pytest tests/test_identity.py -v
python -m pytest tests/test_teamwork.py -v
python -m pytest tests/test_payments_providers.py -v
```

---

## Templates

### Team Templates

| Template | Agents | Quality Gates | Description |
|----------|--------|---------------|-------------|
| `solo` | 1 | Basic check (7.0) | Single agent, individual developers |
| `small_team` | 4 | Expert review (8.0) + QA score (8.5) | Collaborative with keyword routing |
| `enterprise` | 6 | Expert (8.5) + QA (9.0) + Security (9.0) | Production-grade, skill-based routing |

### Service Templates

| Template | Category | Price/Call | Free Tier | Description |
|----------|----------|-----------|-----------|-------------|
| `ai_api` | AI | $0.05 | 100 calls | ML inference API |
| `data_pipeline` | Data | $0.10 | 50 calls | Data processing and ETL |
| `content_api` | Content | $0.02 | 200 calls | Text generation |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests first (TDD recommended)
4. Ensure all tests pass (`python -m pytest tests/ -v`)
5. Submit a pull request with a clear description

### Code Standards

- Python 3.11+
- Immutable data models (frozen dataclasses)
- Comprehensive input validation at all boundaries
- All errors return consistent `{"detail": "..."}` format
- No hardcoded secrets -- use environment variables

---

## License

MIT

---

Built by [JudyAI Lab](https://judyailab.com) with Agent Commerce Framework.
