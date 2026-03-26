# AgenticTrade MCP Server

An MCP (Model Context Protocol) server that connects AI agents to the [AgenticTrade](https://agentictrade.io) marketplace — discover, call, and pay for API services.

## What is AgenticTrade?

AgenticTrade is an API marketplace designed for AI agents. Instead of hardcoding API keys and endpoints, your agent discovers services at runtime, calls them through a payment proxy, and pays per call in USDC. This MCP server exposes the marketplace as tools that any MCP-compatible agent can use.

## Tools

| Tool | Description | Auth Required |
|------|-------------|:---:|
| `discover_services` | Search/browse available API services | No |
| `get_service_details` | Get full details of a specific service | No |
| `call_service` | Call a service through the payment proxy | Yes |
| `get_balance` | Check your agent's USDC balance | Yes |
| `list_categories` | List all service categories | No |

## Installation

### pip

```bash
pip install agentictrade-mcp
```

### uv (recommended)

```bash
uv pip install agentictrade-mcp
```

### From source

```bash
git clone https://github.com/judyailab/agentictrade-mcp.git
cd agentictrade-mcp
pip install -e .
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|:--------:|-------------|
| `AGENTICTRADE_BASE_URL` | No | API base URL (default: `https://agentictrade.io`) |
| `AGENTICTRADE_API_KEY` | For paid calls | Your API key in `key_id:secret` format |
| `AGENTICTRADE_BUYER_ID` | For balance checks | Your buyer/agent ID |

### Get an API Key

1. Visit [agentictrade.io/api-docs](https://agentictrade.io/api-docs)
2. Create a buyer key via `POST /api/v1/keys`
3. Fund your account with USDC, crypto, or PayPal

## Usage

### Claude Desktop

Add to your `claude_desktop_config.json`:

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

### Cursor

Add to your MCP configuration in Cursor settings:

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

### Smithery

This server is available on the [Smithery registry](https://smithery.ai). Install via:

```bash
npx @smithery/cli install agentictrade-mcp
```

### Augment Code

Register as an MCP tool source in Augment Code settings. The server runs on stdio transport and is compatible with any MCP client.

### Programmatic (Python)

```python
from agentictrade_mcp.server import mcp

# Run with stdio transport (default)
mcp.run(transport="stdio")

# Or with SSE for remote connections
mcp.run(transport="sse", port=8080)
```

## Tool Details

### discover_services

Search the marketplace for APIs your agent can use.

```
Parameters:
  query        (string)  — Search keywords (e.g., "crypto scanner")
  category     (string)  — Filter by category (e.g., "crypto", "data")
  max_results  (int)     — Max results, 1-100 (default: 20)

Returns: List of services with id, name, description, pricing, quality scores
```

### get_service_details

Get complete information about a specific service.

```
Parameters:
  service_id  (string)  — Service UUID from discover_services

Returns: Full service info including endpoints, pricing, payment method, tags
```

### call_service

Make a paid API call through the AgenticTrade proxy.

```
Parameters:
  service_id  (string)  — Service UUID to call
  api_key     (string)  — API key (or set AGENTICTRADE_API_KEY env var)
  payload     (string)  — JSON string of the request body
  path        (string)  — Optional sub-path (e.g., "/api/scan")
  method      (string)  — HTTP method (default: "POST")

Returns: Provider response with billing info (usage_id, amount, latency)
```

### get_balance

Check available funds before making calls.

```
Parameters:
  api_key   (string)  — API key (or set AGENTICTRADE_API_KEY env var)
  buyer_id  (string)  — Buyer ID (or set AGENTICTRADE_BUYER_ID env var)

Returns: Current balance, total deposited, total spent (all in USDC)
```

### list_categories

Browse what types of APIs are available.

```
Parameters: none

Returns: List of categories with service counts
```

## Example Agent Flow

```
1. list_categories()
   → See available categories: crypto, data, ai, ...

2. discover_services(query="crypto price", category="crypto")
   → Find services: CoinSifter Scanner (id: svc-abc, $0.01/call)

3. get_service_details(service_id="svc-abc")
   → Confirm pricing, check free tier, read description

4. get_balance()
   → Balance: $42.50 USDC

5. call_service(service_id="svc-abc", payload='{"symbol": "BTC"}')
   → Response: { "price": 67000, ... }
   → Billing: $0.01 deducted
```

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/judyailab/agentictrade-mcp.git
cd agentictrade-mcp
pip install -e ".[dev]"

# Run tests
pytest

# Run server locally
AGENTICTRADE_BASE_URL=https://agentictrade.io agentictrade-mcp
```

## License

MIT License. See [LICENSE](LICENSE).

## Links

- **Marketplace**: [agentictrade.io](https://agentictrade.io)
- **API Docs**: [agentictrade.io/api-docs](https://agentictrade.io/api-docs)
- **MCP Protocol**: [modelcontextprotocol.io](https://modelcontextprotocol.io)
- **Smithery Registry**: [smithery.ai](https://smithery.ai)
- **Built by**: [JudyAI Lab](https://judyailab.com)
