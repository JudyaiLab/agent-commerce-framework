# MCP Commerce Server Template

Pre-configured MCP server that lets any LLM (Claude, GPT, etc.) buy and sell
services on the AgenticTrade marketplace through natural language.

## What This Does

Your LLM agent gets these tools:
- `search_services` — Find services by keyword or category
- `get_service_details` — Price, reputation, free tier info
- `buy_service` — Call a service and pay automatically
- `check_balance` — View current USDC balance
- `check_budget` — Track spending against budget limit
- `get_recommendations` — Smart service suggestions

## Quick Start with Claude Desktop

```bash
# 1. Install dependencies
pip install mcp httpx pyyaml

# 2. Configure
cp config.example.yaml config.yaml
# Edit with your AgenticTrade API key

# 3. Add to Claude Desktop config
# Copy claude_desktop_config.json to your Claude Desktop settings

# 4. Restart Claude Desktop — the tools appear automatically
```

## Claude Desktop Configuration

Add this to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentictrade": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "ACF_API_KEY": "your_key_id:your_secret",
        "ACF_BASE_URL": "https://agentictrade.io"
      }
    }
  }
}
```

## Example Conversation

> **You:** Find me a crypto analysis service and run a scan on BTC

> **Claude:** I'll search the marketplace for crypto analysis services.
> [Uses `search_services` tool with query "crypto analysis"]
>
> Found 2 services:
> 1. CoinSifter — Crypto Market Scanner ($0.50/call, 5 free calls)
> 2. Strategy Backtest API ($2.00/call, 3 free calls)
>
> Let me use CoinSifter to scan BTC.
> [Uses `buy_service` tool]
>
> Here are the results: BTC RSI is 62.3, MACD shows bullish crossover...
