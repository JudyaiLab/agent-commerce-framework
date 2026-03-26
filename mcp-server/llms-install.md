# AgenticTrade MCP Server — Installation Guide

## Quick Install

```bash
pip install agentictrade-mcp
```

Or with uv:

```bash
uv pip install agentictrade-mcp
```

## Configure for Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "agentictrade": {
      "command": "agentictrade-mcp",
      "env": {
        "AGENTICTRADE_API_KEY": "your_key_id:your_secret",
        "AGENTICTRADE_BUYER_ID": "your_buyer_id"
      }
    }
  }
}
```

## Configure for Cursor

Add to MCP configuration in Cursor settings:

```json
{
  "agentictrade": {
    "command": "agentictrade-mcp",
    "env": {
      "AGENTICTRADE_API_KEY": "your_key_id:your_secret"
    }
  }
}
```

## Get an API Key

1. Visit https://agentictrade.io/api-docs
2. Create a buyer key via POST /api/v1/keys
3. Fund your account with USDC, crypto, or PayPal

## Verify Installation

Run the server directly to verify:

```bash
agentictrade-mcp
```

The server starts on stdio transport. It provides 5 tools: discover_services, get_service_details, call_service, get_balance, list_categories.
