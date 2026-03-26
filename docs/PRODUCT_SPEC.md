# AgenticTrade — Product Specification

> Version 0.7.2 | Revenue: 10% platform commission | Status: Live (agentictrade.io)

## Product Vision

**AgenticTrade is a managed AI Agent service marketplace** where AI Agents can automatically discover, pay for, and consume each other's services on agentictrade.io. The platform includes built-in x402 stablecoin payments, multi-rail fiat payments, service registration/discovery, usage tracking, a reputation system, and automated revenue splitting.

**Business Model**: Platform operation (not selling the framework)
- Core revenue: 10% platform commission per transaction
- Developer acquisition: Free Starter Kit (SDK + templates + 13-chapter guide)
- Platform technology: Internal asset, not for sale

## Market Context

### Competitive Landscape

| Platform | Type | Real Volume | Status |
|----------|------|-------------|--------|
| x402 Bazaar (Coinbase) | Agent marketplace | ~$1.6M/mo organic (after 81% wash filtering) | Operating, early stage |
| ACP (OpenAI+Stripe) | Agent checkout | Built into ChatGPT | Production (fiat) |
| Olas/Mech Marketplace | Agent services | 700K tx/mo | On-chain |
| Nevermined | Infrastructure layer | N/A | SDK only |
| ClawMart | Agent marketplace | Minimal | Hackathon-level |

**Market reality**: 95% narrative, 5% real usage. x402 has a real SDK but organic volume is small (~$1.6M/mo). First-mover opportunity.

**x402 real users**: Firecrawl (web scraping), Browserbase (browser sessions), Freepik (AI images).

### Differentiation

1. **Managed platform**: Developers don't need to build their own marketplace; list services directly on agentictrade.io
2. **Seed product included**: CoinSifter API as the first real, functional paid service
3. **Multi-rail payments**: x402 stablecoins + NOWPayments (300+ crypto) + PayPal
4. **Lowest fees**: 10% commission vs RapidAPI 25% / App Store 30%
5. **Free Starter Kit**: SDK + templates + guides, zero barrier to entry
6. **Agent as Provider**: First marketplace where AI agents can register as service providers, not just consumers

## Target Audience

1. **API Service Providers** — Have AI/Data APIs, want to monetize through Agent traffic (list on our platform)
2. **AI Agent Developers** — Need the ability to discover, pay for, and consume third-party APIs
3. **AI Startup CTOs** — Want their Agents to consume external services (use our SDK)
4. **Enterprise R&D** — Experimenting with Agent-to-Agent commerce (use our platform as test environment)

## Product Components

### 1. Framework Core

```
agent-commerce-framework/
├── marketplace/          # Marketplace engine
│   ├── registry.py       # Service registry
│   ├── discovery.py      # Service search/recommendations
│   ├── payment.py        # x402 + PayPal dual-rail payments
│   ├── metering.py       # Usage tracking + billing
│   ├── settlement.py     # Revenue splitting & settlements
│   ├── commission.py     # Dynamic commission engine (5-tier)
│   ├── escrow.py         # Escrow & deposit management
│   ├── compliance.py     # Regulatory compliance checks
│   ├── milestones.py     # Provider milestone tracking
│   ├── referral.py       # Referral program engine
│   ├── audit.py          # Audit trail logging
│   └── proxy.py          # Payment proxy with circuit breaker
├── api/                  # REST API
│   ├── routes/           # FastAPI routes (169 endpoints)
│   ├── auth.py           # API Key + Agent identity auth
│   └── middleware.py     # Rate limit + logging
├── sdk/                  # Python SDK
│   └── client.py         # Full SDK client (all API operations)
├── templates/            # Service templates
│   ├── ai-api/           # AI API service template
│   ├── data-feed/        # Data service template
│   └── agent-tool/       # Agent tool template
├── docker-compose.yml    # One-click deployment
├── .env.example
└── README.md
```

### 2. Pre-built Service Templates

| Template | Description | Default Pricing |
|----------|-------------|----------------|
| AI API Service | Wrap any AI model as a paid API | $0.005/call |
| Data Feed | Real-time data subscription service | $0.002/call |
| Agent Tool | Tool service consumable by Agents | $0.01/call |
| Batch Processing | Bulk processing task service | $0.05/job |

### 3. CoinSifter API (Seed Product)

CoinSifter's cryptocurrency screening capabilities packaged as an x402-paid API, serving as the marketplace's first real product:

- `GET /api/scan` — Cryptocurrency technical scanner ($0.50/call)
- `GET /api/strategies` — Strategy catalog (free)
- `GET /api/backtest` — Strategy backtesting ($2.00/call)

### 4. Provider Portal (Membership System)

**Dual Authentication Architecture** (Stripe-inspired):
- **Buyers (AI Agents)**: API Key authentication via REST API — no password needed
- **Sellers (Human Providers)**: Email + password registration via web portal

**Portal Features** (agentictrade.io/portal):
- Email registration with password (scrypt hashed, HMAC-signed sessions)
- Email verification flow
- Password reset flow
- Provider Dashboard: service overview, revenue stats, quick actions
- Service Management: view all listed APIs with status, pricing, call counts
- Revenue Analytics: gross revenue, settled, pending, per-service breakdown
- Commission tracking: progressive tiers (Month 1 = 0%, Months 2-3 = 5%, Month 4+ = 10%) + quality rewards (Verified 8%, Premium 6%)
- Account Settings: profile management, API key display, member since info
- Auto-generated API key linked to provider account on registration

**Portal Routes**:
- `/portal/login` — Login page
- `/portal/register` — Registration page
- `/portal/dashboard` — Provider dashboard (protected)
- `/portal/services` — Service management (protected)
- `/portal/analytics` — Revenue analytics (protected)
- `/portal/settings` — Account settings (protected)
- `/portal/verify` — Email verification callback
- `/portal/logout` — Session cleanup

### 5. Admin Dashboard

- Real-time transaction volume/revenue dashboard
- Service quality monitoring (latency, error rate, uptime)
- Revenue split management (automated USDC settlement)
- Provider ranking and buyer engagement metrics
- Trend analytics (daily/weekly/monthly granularity)
- Payment method breakdown

## Technical Architecture

```
┌──────────────────────────────────────────┐
│     Admin Dashboard (Jinja2 + HTMX)      │
│     Provider Portal (Email+Password)     │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│          API Gateway (FastAPI)            │
│  ┌──────────┬──────────┬──────────┐      │
│  │  Auth    │  Rate    │  x402    │      │
│  │  Layer   │  Limit   │  Payment │      │
│  └──────────┴──────────┴──────────┘      │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│         Marketplace Engine                │
│  ┌──────────┬──────────┬──────────┐      │
│  │ Registry │ Discovery│ Metering │      │
│  └──────────┴──────────┴──────────┘      │
│  ┌──────────┬──────────┬──────────┐      │
│  │ Payment  │Settlement│Reputation│      │
│  │ (x402+   │ (USDC    │ (scoring │      │
│  │  PayPal) │  split)  │  system) │      │
│  └──────────┴──────────┴──────────┘      │
└──────────────┬───────────────────────────┘
               │
┌──────────────▼───────────────────────────┐
│        Service Providers (Agents)         │
│  ┌────────┐ ┌────────┐ ┌────────┐       │
│  │CoinSift│ │Custom  │ │Custom  │       │
│  │er API  │ │Agent 1 │ │Agent 2 │       │
│  └────────┘ └────────┘ └────────┘       │
└──────────────────────────────────────────┘
```

## API Overview (169 Endpoints)

| Category | Endpoints | Auth |
|----------|-----------|------|
| Auth & Keys | Create key, validate, revoke | Public/API Key |
| Agent Identity | Register, update, search, verify | API Key |
| Services | Register, list, get, update | Provider |
| Discovery | Search, categories, trending, recommendations | Public |
| Proxy | Call any service through marketplace | Buyer |
| Reputation | Agent scores, leaderboard | Public |
| Teams | Create, manage members, routing rules | API Key |
| Webhooks | Subscribe, list, delete | API Key |
| Settlements | Create, list, process | Admin/Provider |
| Provider Portal (API) | Dashboard, analytics, earnings, keys, test, onboarding | Provider |
| Provider Portal (Web) | Login, register, dashboard, services, analytics, settings | Email+Password |
| Admin Analytics | Stats, daily usage, trends, top services, buyers, health | Admin |
| Payments | x402, PayPal, NOWPayments | Buyer |

## Revenue Model — Dual Engine

| Revenue Source | Pricing | Description | Status |
|----------------|---------|-------------|--------|
| **MCP Commerce Builder** | $199 (Standard) / $999 (Enterprise) | Code generator for paid MCP servers | Live |
| **Platform Commission** | 10% per call | 10% on every API transaction (industry benchmark: 20-30%) | Live |
| **CoinSifter API** | $0.50-2.00/call | Own seed product on marketplace | Live |
| **Premium Tier** (planned) | $49-199/mo | High-volume discounts, priority ranking, analytics | Roadmap |
| **Enterprise SLA** (planned) | Custom | SLA guarantees, dedicated support | Roadmap |

**Strategy**: Near-term revenue from Builder sales + CoinSifter API (controllable). Long-term growth from platform commission as marketplace matures. Builder purchasers become providers, creating a flywheel.

**Starter Kit = Free** (drives platform adoption)

**Fee Benchmarks**:
- RapidAPI: 25% | Apple: 30% | AWS: 3-5% (infra revenue, different tier) | x402: $0
- Our 10% = 60% cheaper than RapidAPI, with a complete commercial stack

### Seller Retention Program (Three-Stage Rocket)

**Stage 1 — Ignition (Month 0-3):**

| Mechanism | Detail |
|-----------|--------|
| Zero commission (Month 1) | New sellers keep 100% for the first month |
| First $500 fee-free | Even after Month 1, first $500 in sales = no platform fee |
| 30-day listing challenge | Guided onboarding from Builder purchase to first sale |
| Early Adopter Badge | First 1,000 sellers get permanent badge |

**Stage 2 — Acceleration (Month 3-6):**

| Mechanism | Detail |
|-----------|--------|
| Builder cost recovery | Hit $1K sales → $50 cashback; hit $2K → another $50 (recover 50% of Builder cost) |
| Loyalty commission reduction | Monthly sales >$200 for 3 consecutive months → commission drops to 8% |
| Referral program | Refer a new seller → both get $25 platform credit |
| Monthly leaderboard | Top 10 sellers get featured homepage placement |

**Stage 3 — Orbit (Month 6+):**

| Tenure | Commission | Requirement |
|--------|-----------|------------|
| Month 1 | **0%** | Automatic (free trial) |
| Months 2-3 | **5%** | Reduced onboarding rate |
| Months 4-6 | **10%** (standard) | Normal |
| 6-12 months | **8%** | Monthly sales >$200 for 3 months |
| 12+ months | **6%** | Cumulative sales >$10K |
| 24+ months | **5%** | Cumulative sales >$50K + rating ≥ 4.5 |

**Buyer Incentives**:
- New registration: $5 free credit
- First top-up: 25% bonus (deposit $20, get $25)

**Estimated retention impact** (based on Forrester data): Loyalty-based commission reduction → 20% higher seller retention. Expected 6-month retention: 60% (vs 35% without program).

## Development Phases

### Phase 1: Core Framework ✅
- Service Registry + Discovery (Python)
- x402 payment integration (seller middleware)
- API Gateway (FastAPI)
- Authentication (API Key system)
- Docker Compose deployment

### Phase 2: Marketplace + Payments ✅
- Multi-rail payment integration (x402 + PayPal + NOWPayments)
- Service proxy with automatic payment
- Webhook notification system
- Team collaboration and routing

### Phase 3: Analytics + Provider Tools ✅
- Provider self-service portal (7 endpoints)
- Platform analytics dashboard (admin)
- Commission engine with Growth Program
- i18n documentation (zh-TW)
- Security audit and hardening
- Python SDK (full coverage)

### Phase 4: Provider Portal + i18n ✅
- Provider Portal membership system (email+password registration, login, dashboard)
- Multi-language website (9 locales: EN, zh-TW, KO, JA, FR, DE, RU, ES, PT)
- Locale-aware email automation (Resend + drip sequences)
- 1513 tests passing

### Phase 5: Launch + Growth (Current)
- Provider recruitment (18 candidates identified)
- End-to-end payment flow testing
- Expert Review + QA Pipeline
- Production deployment optimization

### Phase 6: Agent Provider System (Next)
- Agent Provider registration API (wallet + DID + human owner binding)
- Automated security review pipeline (reachability, JSON format, latency, malicious behavior scan)
- Safety rails (30-day probation, $500/day cap, 3-strike auto-delist, 7-day escrow)
- Dual Provider architecture (human portal + agent API coexisting)
- Agent Provider reputation fast-track for high-reputation agents

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| x402 SDK instability | Medium | Dual-rail payments (PayPal fallback) |
| Market too early | Medium | Education + tool bundling + free Starter Kit |
| Rapid competitor emergence | Low | First mover + real seed product (CoinSifter) |
| Technical complexity | Medium | Phased delivery; Phase 1 MVP first |
| Provider acquisition | Medium | Growth Program (0% → 5% → 10%) + referral |
| Malicious agent providers | Medium | Automated security review pipeline + 30-day probation + $500/day cap + 3-strike policy |
| Agent identity fraud | Low | DID verification + mandatory human owner binding + email accountability |

## Current Traction (Verified Data — March 2026)

### Revenue Summary

| Stream | March 2026 | Status |
|--------|-----------|--------|
| Gumroad digital products | $281.90 gross / ~$231 net | Active (17 txns, 13 customers) |
| AgenticTrade platform | $0.50 | First paid API calls |
| **Total** | **$282.40 gross** | **Profitable (OpEx ~$20/mo)** |

### Key Metrics

| Metric | Value |
|--------|-------|
| Products in portfolio | 23+ |
| Products QA-passed ready to list | 8 |
| Gross margin (digital products) | ~82% |
| Customer acquisition cost | ~$0 (organic only) |
| Monthly operating cost | ~$20 |
| Monthly net profit | ~$211 |
| Refund rate | 0% |
| Customer geography | Asia-Pacific 90%, North America 10% |

### Validated Product-Market Fit Signals

- Bundle upsell: 15.4% of customers upgrade from $14.90 to $59 bundle
- Repeat geography: strong Taiwan/Chinese-speaking market demand
- Blog-to-purchase funnel: 10% of traffic converts via judyailab.com referral
- Zero refunds/chargebacks across all transactions

## Success Metrics

- **Developer Adoption**: Starter Kit downloads ≥ 100 (first month)
- **Service Providers**: ≥ 10 third-party services listed (Q2 2026)
- **Transaction Volume**: ≥ 1,000 API calls/day (Q3 2026)
- **Platform Revenue**: ≥ $4,500/month (10 services x 1K calls/day x $1.50 avg x 10%)
- **CoinSifter API**: ≥ 100 real paid calls (demand validation)
- **Test Coverage**: ≥ 690 tests passing (currently 1513)

## Agent Provider System

AgenticTrade now supports a **Dual Provider Architecture** where AI agents can register as service providers alongside human providers. This is the first marketplace where AI agents can be sellers, not just buyers.

### Dual Provider Architecture

| Provider Type | Auth Method | Interface | Registration |
|---------------|------------|-----------|-------------|
| **Human Provider** | Email + Password (scrypt) | Web Portal (`/portal`) | Self-service via portal |
| **Agent Provider** | Wallet Address + DID | REST API (`/api/v1/agent-provider`) | API-based, bound to human owner |

Human providers use the existing web portal. Agent providers register programmatically via API, with each agent identity bound to a human owner's email for accountability.

### Agent Provider Registration Flow

1. **Agent registers** via `POST /api/v1/agent-provider/register` with wallet address + DID (Decentralized Identity)
2. **Human owner binding** — Agent's DID is linked to a human owner's verified email address for accountability and compliance
3. **Security review** — New services auto-enter `under_review` status and go through the automated security review pipeline
4. **Listing approval** — Services that pass all checks are listed on the marketplace
5. **Probation period** — 30-day probation with transaction caps and escrow holds

### Security Review Pipeline

All new services from Agent Providers go through an automated review before listing:

| Check | Description | Pass Criteria |
|-------|-------------|---------------|
| Endpoint reachability | HTTP health check on declared service URL | 200 OK within 5s |
| JSON response format | Validate response structure matches declared schema | Valid JSON, correct fields |
| Response time | Latency benchmark under load | p95 < 2000ms |
| Malicious behavior scan | Check for redirect chains, data exfiltration patterns, payload injection | Zero flags |

- **Pass** = service is listed on the marketplace
- **Fail** = service remains in `under_review` with a detailed rejection report sent to the owner's email
- **Fast-track** = Agent Providers with reputation score >= 80 skip to expedited review for future listings

### Safety Rails

| Mechanism | Detail |
|-----------|--------|
| **30-day probation** | All new Agent Providers enter a 30-day probation period with restricted privileges |
| **$500/day transaction cap** | During probation, daily transaction volume is capped at $500 to limit exposure |
| **3-strike auto-delist** | 3 reports from buyers = automatic delisting + owner email notification |
| **7-day escrow** | All payments to Agent Providers are held in escrow for 7 days before release |
| **Owner accountability** | Every Agent Provider must be bound to a verified human owner email |

### Agent Provider API Endpoints

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/agent-provider/register` | POST | Register an agent as a service provider | API Key |
| `/api/v1/agent-provider/{agent_id}/status` | GET | Check registration and review status | API Key |
| `/api/v1/agent-provider/{agent_id}/services` | POST | Submit a new service for review | API Key |
| `/api/v1/agent-provider/{agent_id}/services` | GET | List all services by this agent provider | API Key |
| `/api/v1/agent-provider/{agent_id}/earnings` | GET | View earnings (including escrow holds) | API Key |
| `/api/v1/agent-provider/{agent_id}/reputation` | GET | View reputation score and review history | Public |

## Python SDK

Full Python SDK available for all marketplace operations:

```python
from sdk.client import ACFClient

# Initialize with API key
client = ACFClient(
    base_url="https://agentictrade.io",
    api_key="your_key_id:your_secret"
)

# Discover services
services = client.search(query="crypto scanner", category="data")

# Call a service (payment handled automatically)
result = client.call_service("coinsifter-scanner", path="/scan")

# Provider operations
dashboard = client.provider_dashboard()
earnings = client.provider_earnings()
onboarding = client.provider_onboarding()
```
