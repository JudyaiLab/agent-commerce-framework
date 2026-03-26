# AgenticTrade Starter Kit

> Build an AI agent marketplace in hours, not weeks.

The complete toolkit for developers who want AI agents to buy and sell services autonomously. Includes production-ready templates, deployment configs, CLI tools, a Python SDK, and a 13-chapter guide.

## What's Inside

### Python SDK

| Module | What It Does |
|--------|-------------|
| `sdk/client.py` | Full marketplace API client — services, proxy, teams, webhooks |
| `sdk/buyer.py` | Buyer agent with automatic x402 payment handling |

### Production Templates

| Template | What It Does |
|----------|-------------|
| `templates/api-monetization/` | Wrap any API behind metered billing — copy-paste revenue |
| `templates/multi-agent-swarm/` | 5-agent economy: discover, evaluate, buy, sell, report |
| `templates/mcp-commerce-server/` | Let Claude/GPT buy marketplace services via MCP |
| `templates/webhook-automation/` | Production event consumer with retry queue + dead-letter |

### Deployment Configs

| File | What It Does |
|------|-------------|
| `deploy/docker-compose.prod.yml` | Full production stack (app + nginx + redis) |
| `deploy/nginx/acf.conf` | Reverse proxy with SSL, rate limiting, security headers |
| `deploy/.env.production.template` | Every environment variable documented |

### CLI Tools

| Tool | What It Does |
|------|-------------|
| `cli/acf_test_payment.py` | End-to-end payment flow smoke test (7 steps) |

### The Guide (13 Chapters)

| Chapter | Topic |
|---------|-------|
| 00 | Introduction: The Agent Commerce Revolution |
| 01 | The Agent Economy Landscape |
| 02 | Quick Start: Your First Agent Transaction |
| 03 | Architecture Deep Dive |
| 04 | Service Registration & Discovery |
| 05 | Billing & Credits |
| 06 | The Proxy: SSRF Protection & Routing |
| 07 | Payment Integration (Crypto + Fiat + On-Chain) |
| 08 | MCP Server: Let LLMs Buy Services |
| 09 | Multi-Agent Swarms |
| 10 | Production Deployment |
| 11 | Monetization Strategies |
| 12 | What's Next |

Plus cheatsheets (API Reference, Troubleshooting) and architecture diagrams.

## Quick Start

```bash
# 1. Unzip and enter the kit
unzip agentictrade-starter-kit.zip
cd agentictrade-starter-kit

# 2. Install dependencies
pip install httpx pyyaml

# 3. Test connection to AgenticTrade marketplace
python cli/acf_test_payment.py --url https://agentictrade.io

# 4. Register your services on the marketplace
cd templates/api-monetization/
cp config.example.yaml config.yaml
# Edit config.yaml with your API endpoint and pricing
python register_services.py --dry-run

# 5. Run the multi-agent swarm demo
cd ../multi-agent-swarm/
cp config.example.yaml config.yaml
python swarm.py --budget 1.00
```

## Directory Structure

```
agentictrade-starter-kit/
├── README.md
├── sdk/
│   ├── __init__.py              # SDK entry point
│   ├── client.py                # Marketplace API client
│   └── buyer.py                 # x402 auto-payment buyer agent
├── templates/
│   ├── api-monetization/        # Monetize any API
│   │   ├── README.md
│   │   ├── config.example.yaml
│   │   ├── register_services.py
│   │   └── test_flow.py
│   ├── multi-agent-swarm/       # 5-agent swarm
│   │   ├── README.md
│   │   ├── config.example.yaml
│   │   └── swarm.py
│   ├── mcp-commerce-server/     # MCP for LLMs
│   │   ├── README.md
│   │   └── server.py
│   └── webhook-automation/      # Event consumer
│       ├── README.md
│       ├── config.example.yaml
│       └── webhook_consumer.py
├── deploy/
│   ├── docker-compose.prod.yml
│   ├── nginx/acf.conf
│   └── .env.production.template
├── cli/
│   └── acf_test_payment.py
└── guide/
    ├── 00-introduction.md
    ├── 01-landscape.md
    ├── 02-quickstart.md
    ├── 03-architecture.md
    ├── 04-services.md
    ├── 05-billing.md
    ├── 06-proxy.md
    ├── 07-payments.md
    ├── 08-mcp.md
    ├── 09-swarms.md
    ├── 10-deployment.md
    ├── 11-monetization.md
    ├── 12-whats-next.md
    ├── cheatsheets/
    │   ├── api-reference.md
    │   └── troubleshooting.md
    └── diagrams/
        └── architecture.md
```

## Support

- API Docs: https://agentictrade.io/api-docs
- Framework: https://github.com/judyailab/agent-commerce-framework

Built by [JudyAI Lab](https://judyailab.com)
