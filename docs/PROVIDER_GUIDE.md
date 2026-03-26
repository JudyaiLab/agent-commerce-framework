---
title: "AgenticTrade Provider Onboarding Guide"
description: "The complete developer guide to listing, configuring, and monetizing your AI API on AgenticTrade — from signup to first automated payment."
date: 2026-03-21
tags: ["agentictrade", "api", "developers", "onboarding", "provider"]
categories: ["Developer Guide"]
---

# AgenticTrade Provider Onboarding Guide

Welcome to AgenticTrade. This guide walks you through the entire provider journey — from creating your account to receiving your first automated micro-payment from an AI agent. Estimated time: **20–30 minutes**. No prior blockchain experience required.

## What You're Building Toward

AgenticTrade is a marketplace where AI agents discover, authenticate, and pay for APIs automatically. As a provider, you list your API once. From that point, any compatible agent can find it, call it, and pay for it — without you sending a single invoice or chasing a single payment.

The platform sits between your API and the agent. It handles discovery (via MCP Tool Descriptors), billing (micro-denomination settlements in USDC/USDT or fiat), authentication (proxy keys), and reputation (transaction history + ratings).

## Step 1: Create Your Provider Account

### Option A: Web Portal (Recommended)

The fastest way to get started. Visit [agentictrade.io/portal/register](https://agentictrade.io/portal/register) and complete the registration form:

1. Enter your email, display name, and password
2. Confirm your email via the verification link
3. You'll be redirected to your **Provider Dashboard** automatically

The portal generates your **Vendor API Key** during registration. Find it under **Settings → API Token** in the dashboard.

### Option B: API-First (Advanced)

If you prefer programmatic onboarding, start at [agentictrade.io](https://agentictrade.io) and sign up via the API. You'll need:

- A valid email address
- Basic business information (name, website, category)
- **Optional:** A crypto wallet (Coinbase Wallet, MetaMask, or any EVM-compatible wallet) if you want to receive USDC settlements. Not required — you can use PayPal for fiat settlement instead.

Once registered, you'll receive a **Vendor API Key** from your dashboard. This key authenticates all your provider-side API calls. Keep it secret — it has permissions to create proxy keys, publish descriptors, and manage your service listing.

```
# Your Vendor API Key looks like:
atx_vendor_7f8a9b2c3d4e5f6...
```

Store it as an environment variable:

```bash
export AGENTICTRADE_VENDOR_KEY="atx_vendor_your_key_here"
```

### New to Crypto? No Problem

- **USDC is a digital dollar.** 1 USDC = 1 USD, always. It's not a volatile cryptocurrency — it's a stablecoin pegged to the US dollar.
- **You don't need to buy any cryptocurrency.** The platform fully supports fiat settlement via PayPal. Crypto is entirely optional.
- **If you do want to receive USDC:** We recommend [Coinbase Wallet](https://www.coinbase.com/wallet) — free, takes about 2 minutes to set up, and works out of the box with AgenticTrade.
- **Base L2** is Ethereum's fast, low-fee layer. All on-chain settlements happen on Base, so transaction fees are fractions of a cent rather than dollars.

## Step 2: Register Your API Service

Before anything else, the platform needs to know what you're selling. You register your API by calling the service registry endpoint:

```bash
curl -X POST https://api.agentictrade.io/v1/services \
  -H "Authorization: Bearer $AGENTICTRADE_VENDOR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Your API Name",
    "slug": "your-api-slug",
    "description": "What your API does and who it's for.",
    "base_url": "https://api.yourdomain.com/v1",
    "protocol": "rest",
    "auth_type": "bearer",
    "category": ["data", "ml", "utility"],
    "pricing_model": "per_call",
    "price_usd": 0.001,
    "mcp_enabled": true,
    "tags": ["relevant", "keywords"]
  }'
```

The response gives you a `service_id` and confirms your commission tier. New providers automatically receive **Month 1 at 0% commission** — you keep 100% of revenue with no conditions.

### Key Registration Fields

| Field | Notes |
|-------|-------|
| `slug` | Unique identifier used in URLs and API calls. Set once, cannot change. |
| `base_url` | Your actual API endpoint. AgenticTrade proxies calls through here. |
| `pricing_model` | `per_call`, `per_token`, `subscription`, or `tiered`. Most providers start with `per_call`. |
| `price_usd` | Per-call price in USD. You can set per-tool prices in the MCP descriptor for more granularity. |
| `mcp_enabled` | Set to `true` to enable MCP Tool Descriptor publishing. |

## Step 3: Issue a Proxy API Key

Never give agents your raw API key. Instead, create a **proxy key** through AgenticTrade. Proxy keys route through the platform's billing layer, which meters usage, enforces rate limits, and charges the calling agent's wallet — all without touching your existing authentication system.

```bash
curl -X POST https://api.agentictrade.io/v1/services/YOUR_SERVICE_ID/keys \
  -H "Authorization: Bearer $AGENTICTRADE_VENDOR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Agent Key",
    "scope": ["read", "execute"],
    "rate_limit": 1000,
    "rate_limit_window": "minute"
  }'
```

The response contains your `proxy_key`. Give this to agents — it's the only credential they'll need. You can issue multiple proxy keys for different agents or use cases, and revoke them individually without affecting others.

### Proxy Key Structure

```
atx_pk_prod_K8mNpQrStUvWxYz1234567890
 ^^^^ ^^ ^^^^^^
 │    │   └─ Unique key identifier
 │    └─ Environment (prod/staging)
 └─ Prefix (indicates AgenticTrade proxy key)
```

## Step 4: Publish Your MCP Tool Descriptor

The MCP Tool Descriptor is what makes your API **discoverable by AI agents**. It's a JSON schema that describes every tool your API exposes — its name, parameters, return type, and per-call cost. When you publish it, it enters the AgenticTrade MCP registry.

Agents built on MCP-compatible frameworks (LangChain, CrewAI, AutoGPT, and others) can auto-discover your tools, parse the schema, and start calling them without any manual integration on your end.

```bash
curl -X PUT https://api.agentictrade.io/v1/mcp/YOUR_SERVICE_ID/descriptor \
  -H "Authorization: Bearer $AGENTICTRADE_VENDOR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0",
    "name": "your_api_slug",
    "description": "What capability your API provides to agents.",
    "category": "data",
    "tools": [
      {
        "name": "tool_name",
        "description": "What this specific tool does.",
        "input_schema": {
          "type": "object",
          "properties": {
            "param_name": {
              "type": "string",
              "description": "What this parameter controls."
            }
          },
          "required": ["param_name"]
        },
        "pricing": {
          "cost_usd": 0.001,
          "unit": "per_call"
        }
      }
    ],
    "auth": {
      "type": "bearer",
      "proxy_key_hint": "Use your AgenticTrade proxy key as the Bearer token."
    },
    "rate_limits": {
      "requests_per_minute": 1000
    }
  }'
```

### Descriptor Best Practices

- **Be specific in descriptions.** Agents use tool descriptions to decide whether to call your API. Vague descriptions get filtered out by quality-gated discovery.
- **Set per-tool pricing.** If your API has multiple endpoints with different compute costs, price each tool individually rather than averaging.
- **Use real examples.** Add `examples` arrays to parameters when possible — agents learn better from concrete input/output pairs.
- **Publish incrementally.** Start with your 2–3 most useful tools. You can add more later without changing your service registration.

## Step 5: Test the Full Call Flow

Before going live, verify the complete flow end-to-end. Use the AgenticTrade dashboard to simulate an agent call:

```bash
# 1. Agent fetches your descriptor
curl https://api.agentictrade.io/v1/mcp/your-api-slug/descriptor.json

# 2. Agent calls through the proxy (uses an agent wallet key, not your vendor key)
curl -X POST https://api.agentictrade.io/v1/call \
  -H "Authorization: Bearer AGENT_WALLET_KEY" \
  -H "X-Service: your-api-slug" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "tool_name",
    "params": { "param_name": "test_value" }
  }'
```

Your API receives a standard call at `base_url`. The proxy layer adds metering and billing transparently. Check your provider dashboard — you should see the call logged with its cost within 15 minutes.

## Step 6: Understand How You Get Paid

AgenticTrade settles revenue to your connected wallet on a **T+1 rolling basis** — meaning yesterday's call revenue lands in your wallet today. Settlement runs automatically; no invoice generation required.

| Phase | Months | Commission | You Receive |
|-------|--------|------------|-------------|
| Launch Month | Month 1 | **0%** | 100% |
| Growth Phase | Months 2–3 | **5%** | 95% |
| Standard | Month 4+ | **10%** | 90% |

You can receive settlements in USDC, USDT, or fiat (via PayPal integration). Minimum payout threshold is $10 equivalent. Your dashboard shows per-agent call breakdowns, revenue trends, and reputation scores.

## Step 7: Monitor and Optimize

Once live, your provider dashboard is your command center:

- **Call logs**: Every agent call, timestamp, cost, and agent wallet ID
- **Revenue dashboard**: Daily/weekly/monthly revenue with trend charts
- **Reputation score**: Automatically calculated from latency, reliability, and response quality metrics
- **Rate limit monitoring**: See which agents are hitting limits and adjust thresholds

Higher reputation scores improve discovery ranking. Maintain low latency and high reliability to maximize your discoverability in quality-gated agent frameworks.

## Commission Comparison

Here's why this matters financially. At typical AI API margins:

| Monthly Revenue | RapidAPI (25%) | AgenticTrade (10%) | Annual Savings |
|-----------------|---------------|--------------------|-----------------|
| $5,000 | $15,000/yr | $6,000/yr | **$9,000** |
| $20,000 | $60,000/yr | $24,000/yr | **$36,000** |
| $50,000 | $150,000/yr | $60,000/yr | **$90,000** |

The first three months are even better: 0% then 5% commission. There's no reason not to list.

## Dispute Resolution

AgenticTrade uses an escrow system to protect both buyers and providers. When a buyer calls your API, their payment is held in escrow before being released to you. If a buyer disputes a transaction, here's what happens and how to respond.

### Escrow Hold Periods

Hold periods scale with transaction amount — smaller payments clear faster:

| Transaction Amount | Hold Period | Dispute Window |
|--------------------|-------------|----------------|
| Under $1 | 1 day | 24 hours |
| $1 – $100 | 3 days | 72 hours (3 days) |
| Over $100 | 7 days | 7 days |

During the hold period, the buyer can open a dispute. If no dispute is filed, payment is released to you automatically when the hold period ends.

### What Happens When a Buyer Disputes

1. **Buyer opens a dispute** — The buyer submits a reason, selects a category (`service_not_delivered`, `quality_issue`, `unauthorized_charge`, `wrong_output`, `timeout_or_error`, or `other`), and can attach evidence URLs.
2. **You receive a notification** — Check your dashboard or listen for the `escrow.dispute_opened` webhook event.
3. **You submit counter-evidence** — You have until the dispute window closes to respond.
4. **Admin reviews and resolves** — If neither party resolves the dispute, an admin makes a binding decision.
5. **If the dispute window expires without admin action**, the hold is auto-released to you.

### Submitting Counter-Evidence

When a dispute is opened against one of your transactions, respond with your side of the story via the API:

```bash
curl -X POST https://api.agentictrade.io/v1/escrow/holds/{hold_id}/dispute/respond \
  -H "Authorization: Bearer $AGENTICTRADE_VENDOR_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Service was delivered successfully. Logs show a 200 response with correct output at the timestamp in question.",
    "evidence_urls": [
      "https://your-logging-dashboard.com/logs/abc123",
      "https://screenshots.example.com/response-proof.png"
    ]
  }'
```

**Tips for effective counter-evidence:**
- Include server-side logs showing the request was processed correctly
- Provide timestamps that match the disputed transaction
- Link to any monitoring dashboards that confirm uptime and response quality
- Evidence URLs must use `https://` (up to 10 URLs, max 2048 characters each)

### Resolution Outcomes

Every dispute ends in one of three outcomes. Here's how each affects your payout:

| Outcome | What Happens | Your Payout |
|---------|-------------|-------------|
| `release_to_provider` | Dispute ruled in your favor | **Full amount released** to your wallet |
| `refund_buyer` | Dispute ruled in buyer's favor | **$0** — full amount returned to buyer |
| `partial_refund` | Split decision | **Partial amount** — you receive `hold_amount - refund_amount` |

For `partial_refund`, the admin specifies the exact refund amount. The remainder is released to you. For example, on a $10 hold with a $3 partial refund, you receive $7.

### Monitoring Disputes

Track your escrow status through the provider summary endpoint:

```bash
curl https://api.agentictrade.io/v1/escrow/providers/{your_provider_id}/summary \
  -H "Authorization: Bearer $AGENTICTRADE_VENDOR_KEY"
```

This returns your `total_held`, `total_released`, `total_refunded`, and `pending_count`. You can also view individual hold details and dispute evidence from the dashboard.

### Minimizing Disputes

The best way to handle disputes is to avoid them:
- Maintain high uptime and low latency (directly affects your reputation score)
- Return clear error messages when requests fail — agents that understand the error are less likely to dispute
- Set accurate pricing in your MCP descriptor — unexpected charges are a common dispute trigger
- Monitor your call logs for anomalies before buyers notice them

## Ready to Go Live?

Sign up at [agentictrade.io](https://agentictrade.io) — free to list, first month at 0% commission. Your MCP descriptor can be live in under 10 minutes. Then let the agents find you.

---

*Questions? Check the [API documentation](https://docs.agentictrade.io) or email support@agentictrade.io.*
