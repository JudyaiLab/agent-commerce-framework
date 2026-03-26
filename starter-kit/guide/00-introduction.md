# Introduction: The Agent Commerce Revolution

## Why This Guide Exists

In 2025, AI agents learned to write code, search the web, and analyze data. In 2026, they're learning to buy and sell.

The shift from "agents that help humans" to "agents that transact autonomously" is happening faster than most developers realize. Today's agent frameworks (LangChain, CrewAI, AutoGen) handle orchestration beautifully — but they assume a human is always holding the wallet. When Agent A needs a service from Agent B, someone has to manually set up the API key, agree on pricing, and handle payment.

That manual step is the bottleneck. Remove it, and you unlock an entirely new category of applications:

- **A research agent** that autonomously purchases premium data feeds when it needs deeper analysis
- **A trading bot** that pays for real-time sentiment analysis from a specialized service
- **A content pipeline** that hires translation agents on-demand, paying per word
- **A monitoring swarm** where agents buy and sell alert signals to each other

This guide shows you how to build these systems. Not in theory — with production code you can deploy today.

## What You'll Build

By the end of this guide, you'll have:

1. **A running marketplace** where AI agents register, discover, and purchase services
2. **Metered billing** that charges per API call with configurable free tiers
3. **Real payment processing** — crypto (USDC via x402/AgentKit), fiat (PayPal), or both
4. **SSRF-hardened proxy** that safely routes agent-to-agent API calls
5. **MCP integration** so Claude, GPT, and other LLMs can buy services natively
6. **Multi-agent swarms** that autonomously evaluate and purchase services
7. **Production deployment** with Docker, Nginx, SSL, and monitoring

## Who This Is For

This guide assumes you:

- Can write Python (intermediate level)
- Have used Docker before
- Understand REST APIs
- Have heard of AI agents (LangChain, CrewAI, etc.) even if you haven't built one

No blockchain experience needed. No ML expertise required.

## How This Guide Is Organized

### Part I: Foundation (Chapters 1-3)
Understanding the landscape, architecture decisions, and getting your first marketplace running.

### Part II: Hands-On (Chapters 4-7)
Building each component: service registration, billing, proxy routing, and payment integration.

### Part III: Advanced (Chapters 8-10)
MCP servers, multi-agent swarms, and production deployment.

### Part IV: Business (Chapters 11-12)
Monetization strategies, pricing models, and scaling your marketplace.

Each chapter includes:
- **Concept explanation** — why this component exists
- **Code walkthrough** — how it works under the hood
- **Exercise** — build or customize something yourself
- **Checkpoint** — verify everything works before moving on

## The Agent Commerce Framework

This guide is built on the [Agent Commerce Framework](https://github.com/judyailab/agent-commerce-framework) (ACF) — an MIT-licensed, open-source marketplace for AI agent services. The framework handles:

| Component | What It Does |
|-----------|-------------|
| Service Registry | Agents register APIs with pricing and descriptions |
| Discovery | Agents search and evaluate available services |
| Billing | Pre-paid credits with per-call metering |
| Proxy | SSRF-protected routing of agent-to-agent API calls |
| Settlement | Automatic seller payouts |
| Identity | Agent identity verification |
| Reputation | Quality scoring based on usage history |

The Starter Kit adds production templates, deployment configs, and this guide on top of the open-source framework.

## Prerequisites

Before starting, make sure you have:

```bash
# Required
python --version    # 3.10+
docker --version    # 24.0+
docker compose version  # 2.20+

# Optional (for payment integration)
# NOWPayments account → https://nowpayments.io
# Stripe account → https://stripe.com
# Coinbase Developer Platform → https://portal.cdp.coinbase.com
```

Ready? Let's build.

---

*Next: [Chapter 1 — The Agent Economy Landscape →](./01-landscape.md)*
