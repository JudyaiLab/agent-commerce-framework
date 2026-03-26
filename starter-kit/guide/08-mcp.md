# Chapter 8: MCP Server — Let LLMs Buy Services

## What is MCP?

Model Context Protocol (MCP) is Anthropic's standard for giving LLMs access to external tools. Instead of hardcoding API calls, LLMs discover and use tools dynamically through MCP servers.

When you build an MCP Commerce Server, any MCP-compatible LLM (Claude, GPT with MCP support, etc.) can:

- **Search** your marketplace for services
- **Evaluate** service quality and pricing
- **Purchase** services autonomously
- **Monitor** spending and balance

This is the bridge between "AI agent" and "AI agent with a wallet."

## Architecture

```
Claude Desktop / API
        │
        ▼
MCP Commerce Server (your code)
        │
        ▼
ACF Marketplace API
        │
        ▼
Seller APIs
```

The MCP server exposes marketplace operations as tools that the LLM can call.

## Building the MCP Server

The Starter Kit includes a complete MCP Commerce Server at `templates/mcp-commerce-server/server.py`. Here's how each tool works:

### Tool 1: search_services

```python
@server.tool()
async def search_services(
    query: str = "",
    category: str = "",
    max_price: float = 0,
) -> str:
    """Search the marketplace for AI agent services.

    Args:
        query: Search text (matches name and description)
        category: Filter by category (crypto, ai, data, code, utility)
        max_price: Maximum price per call in USD (0 = no limit)

    Returns:
        List of matching services with pricing information.
    """
    params = {}
    if query:
        params["q"] = query
    if category:
        params["category"] = category
    if max_price > 0:
        params["max_price"] = max_price

    r = await client.get(f"{ACF_URL}/api/v1/services", params=params)
    services = r.json()

    # Format for LLM readability
    results = []
    for svc in services:
        results.append({
            "id": svc["id"],
            "name": svc["name"],
            "description": svc["description"],
            "price_per_call": f"${svc['price_per_call']:.4f}",
            "free_tier": f"{svc['free_tier_calls']} calls",
            "category": svc.get("category", "general"),
        })
    return json.dumps(results, indent=2)
```

### Tool 2: buy_service

```python
@server.tool()
async def buy_service(
    service_id: str,
    path: str = "",
    data: str = "{}",
) -> str:
    """Purchase and call an AI agent service.

    This makes a paid API call through the marketplace.
    You'll be charged the service's per-call price.

    Args:
        service_id: The service ID to call
        path: API path to call (appended to service base URL)
        data: JSON string of request body

    Returns:
        The service's response data plus billing information.
    """
    body = json.loads(data) if data else {}

    r = await client.post(
        f"{ACF_URL}/api/v1/proxy/{service_id}/{path}",
        json=body,
        params={"buyer_id": BUYER_ID},
    )

    billing = {
        "charged": r.headers.get("X-ACF-Amount", "0"),
        "free_tier": r.headers.get("X-ACF-Free-Tier", "unknown"),
        "remaining_balance": r.headers.get("X-ACF-Balance", "unknown"),
    }

    return json.dumps({
        "status": r.status_code,
        "billing": billing,
        "data": r.json() if r.status_code < 400 else r.text,
    }, indent=2)
```

### Tool 3: check_balance

```python
@server.tool()
async def check_balance() -> str:
    """Check your current marketplace balance.

    Returns your available credits for purchasing services.
    """
    r = await client.get(f"{ACF_URL}/api/v1/balance/{BUYER_ID}")
    data = r.json()
    return f"Balance: ${data['balance']:.2f} USD"
```

### Tool 4: check_budget

```python
@server.tool()
async def check_budget(
    service_id: str,
    num_calls: int = 10,
) -> str:
    """Estimate cost for multiple service calls.

    Args:
        service_id: Service to estimate costs for
        num_calls: Number of planned calls

    Returns:
        Cost breakdown including free tier savings.
    """
    svc = (await client.get(
        f"{ACF_URL}/api/v1/services/{service_id}"
    )).json()

    free = min(num_calls, svc["free_tier_calls"])
    paid = max(0, num_calls - svc["free_tier_calls"])
    total_cost = paid * svc["price_per_call"]

    return json.dumps({
        "service": svc["name"],
        "planned_calls": num_calls,
        "free_tier_calls": free,
        "paid_calls": paid,
        "price_per_call": f"${svc['price_per_call']:.4f}",
        "estimated_total": f"${total_cost:.2f}",
    }, indent=2)
```

## Connecting to Claude Desktop

Add the MCP server to Claude Desktop's config:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agent-marketplace": {
      "command": "python",
      "args": ["/path/to/mcp-commerce-server/server.py"],
      "env": {
        "ACF_URL": "https://agentictrade.io",
        "ACF_BUYER_ID": "claude-desktop-user",
        "ACF_API_KEY": "your-api-key"
      }
    }
  }
}
```

Restart Claude Desktop. You should see the marketplace tools in the tool list.

## Connecting to Claude Code

```json
// .mcp.json in your project root
{
  "mcpServers": {
    "marketplace": {
      "command": "python",
      "args": ["path/to/server.py"],
      "env": {
        "ACF_URL": "https://agentictrade.io",
        "ACF_BUYER_ID": "claude-code-agent"
      }
    }
  }
}
```

## Example: Claude Buys a Service

Here's what happens when Claude needs data analysis:

```
User: "Analyze the sentiment for Bitcoin and Ethereum right now"

Claude (thinking): I need crypto sentiment data. Let me check the marketplace.

Claude → search_services(query="crypto sentiment")
  Returns: CoinSifter Sentiment API ($0.05/call, 10 free)

Claude → check_balance()
  Returns: $5.00

Claude → check_budget(service_id="svc_123", num_calls=2)
  Returns: 2 calls, both free tier, $0.00 estimated

Claude → buy_service(service_id="svc_123", path="analyze", data='{"symbol":"BTC"}')
  Returns: {sentiment: 0.72, confidence: 85%, sources: 247}

Claude → buy_service(service_id="svc_123", path="analyze", data='{"symbol":"ETH"}')
  Returns: {sentiment: 0.45, confidence: 78%, sources: 183}

Claude: "Bitcoin sentiment is strongly bullish (0.72) with high confidence,
while Ethereum is moderately bullish (0.45). Both analyses were free tier calls."
```

## Security Considerations

### Budget Limits

Always set budget limits for MCP agents:

```python
# In your MCP server config
MAX_SPEND_PER_SESSION = 1.00  # USD
MAX_SINGLE_PURCHASE = 0.50
```

### Confirmation for Large Purchases

```python
@server.tool()
async def buy_service(service_id, path, data):
    svc = await get_service(service_id)
    if svc["price_per_call"] > MAX_SINGLE_PURCHASE:
        return (
            f"This call costs ${svc['price_per_call']:.2f} which exceeds "
            f"the ${MAX_SINGLE_PURCHASE:.2f} limit. Please confirm."
        )
    # ... proceed with purchase
```

### Audit Trail

Every purchase through MCP is logged in the ACF usage records, giving you a complete audit trail of what the LLM bought and why.

## Exercise: Build a Custom MCP Tool

1. Add a `get_recommendations` tool that suggests services based on recent usage
2. Add a `compare_services` tool that shows pricing for similar services
3. Test with Claude Desktop or Claude Code

## Checkpoint

- [ ] Understand MCP and how it enables LLM commerce
- [ ] MCP server running with 4+ tools
- [ ] Connected to Claude Desktop or Claude Code
- [ ] Made at least one purchase through MCP
- [ ] Budget limits configured

---

*Next: [Chapter 9 — Multi-Agent Swarms →](./09-swarms.md)*
