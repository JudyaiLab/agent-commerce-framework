"""AgenticTrade MCP Server.

Exposes five tools that any MCP-compatible AI agent can call:
  - discover_services  — search/browse marketplace
  - get_service_details — full service info
  - call_service        — proxy a request with automatic billing
  - get_balance         — check USDC balance
  - list_categories     — browse service categories

Run via: ``agentictrade-mcp`` (stdio) or import and configure transport.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .client import AgenticTradeClient, AgenticTradeError

logger = logging.getLogger("agentictrade_mcp.server")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

_BASE_URL = os.environ.get("AGENTICTRADE_BASE_URL", "https://agentictrade.io")
_API_KEY = os.environ.get("AGENTICTRADE_API_KEY", "")
_BUYER_ID = os.environ.get("AGENTICTRADE_BUYER_ID", "")

# ---------------------------------------------------------------------------
# MCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "AgenticTrade",
    instructions=(
        "AgenticTrade MCP Server — discover, call, and pay for API services "
        "on the AgenticTrade marketplace (agentictrade.io). "
        "AI agents use this server to find APIs, check pricing, make paid "
        "API calls through the marketplace proxy, and monitor their balance."
    ),
)

# Shared client — created lazily on first tool call
_client: AgenticTradeClient | None = None


def _get_client() -> AgenticTradeClient:
    """Return the shared AgenticTrade API client (lazy singleton)."""
    global _client
    if _client is None:
        _client = AgenticTradeClient(base_url=_BASE_URL)
    return _client


def _format_error(exc: AgenticTradeError) -> str:
    """Format an API error for the LLM to understand."""
    return json.dumps({
        "error": True,
        "status_code": exc.status_code,
        "detail": exc.detail,
    })


# ---------------------------------------------------------------------------
# Tool: discover_services
# ---------------------------------------------------------------------------

@mcp.tool()
async def discover_services(
    query: str = "",
    category: str = "",
    max_results: int = 20,
) -> str:
    """Search and browse available API services on the AgenticTrade marketplace.

    Use this tool to find APIs that your agent can call. You can search by
    keyword (e.g., "crypto", "scanner", "backtest") or filter by category.

    Parameters:
        query: Search query string. Leave empty to browse all services.
        category: Filter by service category (e.g., "crypto", "data", "ai").
            Leave empty for all categories.
        max_results: Maximum number of results to return (1-100, default 20).

    Returns:
        JSON with a list of services. Each service includes:
        - id: unique service ID (use this with get_service_details or call_service)
        - name: human-readable service name
        - description: what the service does
        - pricing: { price_per_call, currency, free_tier_calls }
        - quality: { health_score, uptime_pct } (if available)
        - category and tags for filtering

    Example:
        discover_services(query="crypto scanner", max_results=5)
    """
    client = _get_client()
    try:
        result = await client.discover_services(
            query=query or None,
            category=category or None,
            max_results=max_results,
        )
        return json.dumps(result, indent=2, default=str)
    except AgenticTradeError as exc:
        return _format_error(exc)


# ---------------------------------------------------------------------------
# Tool: get_service_details
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_service_details(service_id: str) -> str:
    """Get full details of a specific API service on AgenticTrade.

    Use this after discover_services to get complete information about
    a service before calling it.

    Parameters:
        service_id: The unique service UUID (from discover_services results).

    Returns:
        JSON with complete service info:
        - id, name, description
        - provider_id: who runs the service
        - pricing: { price_per_call, currency, payment_method, free_tier_calls }
        - status: "active" means ready to call
        - category, tags, created_at, updated_at

    Example:
        get_service_details(service_id="abc123-def456-...")
    """
    if not service_id or not service_id.strip():
        return json.dumps({"error": True, "detail": "service_id is required"})

    client = _get_client()
    try:
        result = await client.get_service_details(service_id.strip())
        return json.dumps(result, indent=2, default=str)
    except AgenticTradeError as exc:
        return _format_error(exc)


# ---------------------------------------------------------------------------
# Tool: call_service
# ---------------------------------------------------------------------------

@mcp.tool()
async def call_service(
    service_id: str,
    api_key: str = "",
    payload: str = "{}",
    path: str = "",
    method: str = "POST",
) -> str:
    """Call an API service through the AgenticTrade payment proxy.

    This routes your request through AgenticTrade, which handles authentication
    with the provider and automatic USDC billing. You pay per call based on
    the service's listed price.

    Parameters:
        service_id: The service UUID to call.
        api_key: Your AgenticTrade API key (format: "key_id:secret").
            If not provided, uses the AGENTICTRADE_API_KEY environment variable.
        payload: JSON string of the request body to send to the service.
            Example: '{"symbol": "BTC", "interval": "1h"}'
        path: Optional sub-path on the service (e.g., "/api/scan").
        method: HTTP method — typically "POST" for service calls.

    Returns:
        JSON with:
        - status_code: HTTP response status from the provider
        - body: the provider's response (parsed JSON or raw text)
        - billing: { usage_id, amount_usd, free_tier, latency_ms }

    Example:
        call_service(
            service_id="abc123-...",
            payload='{"symbol": "ETH", "interval": "4h"}'
        )
    """
    if not service_id or not service_id.strip():
        return json.dumps({"error": True, "detail": "service_id is required"})

    effective_key = api_key.strip() if api_key else _API_KEY
    if not effective_key:
        return json.dumps({
            "error": True,
            "detail": (
                "API key required. Either pass api_key parameter or set "
                "AGENTICTRADE_API_KEY environment variable."
            ),
        })

    # Parse payload from JSON string
    try:
        parsed_payload: dict[str, Any] = json.loads(payload) if payload else {}
    except json.JSONDecodeError as exc:
        return json.dumps({
            "error": True,
            "detail": f"Invalid JSON in payload: {exc}",
        })

    client = _get_client()
    try:
        result = await client.call_service(
            service_id=service_id.strip(),
            api_key=effective_key,
            payload=parsed_payload,
            path=path,
            method=method,
        )
        return json.dumps(result, indent=2, default=str)
    except AgenticTradeError as exc:
        return _format_error(exc)


# ---------------------------------------------------------------------------
# Tool: get_balance
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_balance(
    api_key: str = "",
    buyer_id: str = "",
) -> str:
    """Check your agent's USDC balance on AgenticTrade.

    Use this to verify you have sufficient funds before making paid API calls.

    Parameters:
        api_key: Your AgenticTrade API key (format: "key_id:secret").
            If not provided, uses the AGENTICTRADE_API_KEY environment variable.
        buyer_id: Your buyer/agent ID on the marketplace.
            If not provided, uses the AGENTICTRADE_BUYER_ID environment variable.

    Returns:
        JSON with:
        - buyer_id: your account identifier
        - balance: current USDC balance available for API calls
        - total_deposited: lifetime deposits
        - total_spent: lifetime spend on API calls

    Example:
        get_balance()
    """
    effective_key = api_key.strip() if api_key else _API_KEY
    effective_buyer = buyer_id.strip() if buyer_id else _BUYER_ID

    if not effective_key:
        return json.dumps({
            "error": True,
            "detail": (
                "API key required. Either pass api_key parameter or set "
                "AGENTICTRADE_API_KEY environment variable."
            ),
        })

    if not effective_buyer:
        return json.dumps({
            "error": True,
            "detail": (
                "buyer_id required. Either pass buyer_id parameter or set "
                "AGENTICTRADE_BUYER_ID environment variable."
            ),
        })

    client = _get_client()
    try:
        result = await client.get_balance(effective_key, effective_buyer)
        return json.dumps(result, indent=2, default=str)
    except AgenticTradeError as exc:
        return _format_error(exc)


# ---------------------------------------------------------------------------
# Tool: list_categories
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_categories() -> str:
    """List all service categories available on the AgenticTrade marketplace.

    Use this to discover what types of APIs are available before searching.

    Returns:
        JSON with a list of categories, each containing:
        - name: category name (e.g., "crypto", "data", "ai")
        - count: number of active services in this category

    Example:
        list_categories()
    """
    client = _get_client()
    try:
        result = await client.list_categories()
        return json.dumps(result, indent=2, default=str)
    except AgenticTradeError as exc:
        return _format_error(exc)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the AgenticTrade MCP server on stdio transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        stream=sys.stderr,  # MCP uses stdout for protocol, logs go to stderr
    )
    logger.info("Starting AgenticTrade MCP server (base_url=%s)", _BASE_URL)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
