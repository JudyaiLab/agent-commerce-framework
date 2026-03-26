"""
MCP Commerce Server — Expose AgenticTrade marketplace to LLM agents.

This server provides tools that let Claude, GPT, or any MCP-compatible
LLM discover, evaluate, and purchase services autonomously.

Usage:
    python server.py                          # stdio mode (for Claude Desktop)
    ACF_API_KEY=key:secret python server.py   # with API key from env

Requires: pip install mcp httpx pyyaml
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("MCP SDK not installed. Run: pip install mcp")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("ACF_BASE_URL", "https://agentictrade.io")
API_KEY = os.environ.get("ACF_API_KEY", "")
BUYER_ID = os.environ.get("ACF_BUYER_ID", "mcp-agent")
BUDGET_LIMIT = float(os.environ.get("ACF_BUDGET_LIMIT", "10.0"))

# Track spending within this session
_session_spent = 0.0


def _api(method: str, path: str, **kwargs) -> dict:
    """Make an API call to AgenticTrade."""
    headers = {"Accept": "application/json"}
    if API_KEY:
        headers["Authorization"] = f"Bearer {API_KEY}"
    resp = httpx.request(method, f"{BASE_URL}{path}", headers=headers, timeout=30, **kwargs)
    if resp.status_code >= 400:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:500]}


# ---------------------------------------------------------------------------
# MCP Server
# ---------------------------------------------------------------------------

server = Server("agentictrade-commerce")


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="search_services",
            description="Search the AgenticTrade marketplace for services. "
                        "Returns service name, price, free tier, and category.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword (e.g., 'crypto', 'data')"},
                    "category": {"type": "string", "description": "Filter by category"},
                    "max_price": {"type": "number", "description": "Maximum price per call in USD"},
                },
            },
        ),
        Tool(
            name="get_service_details",
            description="Get detailed info about a specific service including "
                        "description, pricing, reputation score, and free tier.",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "Service ID"},
                },
                "required": ["service_id"],
            },
        ),
        Tool(
            name="buy_service",
            description="Call a marketplace service through the payment proxy. "
                        "Automatically handles billing (free tier or balance deduction).",
            inputSchema={
                "type": "object",
                "properties": {
                    "service_id": {"type": "string", "description": "Service ID to call"},
                    "path": {"type": "string", "description": "API path to call (e.g., '/scan', '/analyze')"},
                    "payload": {"type": "object", "description": "JSON body to send"},
                },
                "required": ["service_id"],
            },
        ),
        Tool(
            name="check_balance",
            description="Check current USDC balance on the marketplace.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="check_budget",
            description="Check how much has been spent this session vs the budget limit.",
            inputSchema={"type": "object", "properties": {}},
        ),
        Tool(
            name="get_recommendations",
            description="Get smart service recommendations based on popularity and reputation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "use_case": {"type": "string", "description": "What you want to accomplish"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    global _session_spent

    if name == "search_services":
        services = _api("GET", "/api/v1/services")
        if isinstance(services, dict) and "error" in services:
            return [TextContent(type="text", text=json.dumps(services))]

        results = []
        query = (arguments.get("query") or "").lower()
        category = (arguments.get("category") or "").lower()
        max_price = arguments.get("max_price")

        for svc in (services if isinstance(services, list) else []):
            if query and query not in svc.get("name", "").lower() and query not in svc.get("description", "").lower():
                continue
            if category and category not in svc.get("category", "").lower():
                continue
            price = float(svc.get("price_per_call", 0))
            if max_price is not None and price > max_price:
                continue
            results.append({
                "id": svc["id"],
                "name": svc["name"],
                "description": svc.get("description", "")[:120],
                "price_per_call": price,
                "free_tier_calls": svc.get("free_tier_calls", 0),
                "category": svc.get("category", ""),
            })

        return [TextContent(type="text", text=json.dumps(results, indent=2))]

    elif name == "get_service_details":
        svc_id = arguments["service_id"]
        svc = _api("GET", f"/api/v1/services/{svc_id}")
        return [TextContent(type="text", text=json.dumps(svc, indent=2))]

    elif name == "buy_service":
        svc_id = arguments["service_id"]
        path = arguments.get("path", "/request")
        payload = arguments.get("payload", {})

        # Budget check
        if _session_spent >= BUDGET_LIMIT:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Session budget limit reached (${BUDGET_LIMIT:.2f}). "
                         f"Spent: ${_session_spent:.2f}",
            }))]

        headers = {"Accept": "application/json"}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"

        resp = httpx.post(
            f"{BASE_URL}/api/v1/proxy/{svc_id}{path}",
            headers=headers, json=payload,
            params={"buyer_id": BUYER_ID}, timeout=30,
        )

        amount = float(resp.headers.get("X-ACF-Amount", "0"))
        free_tier = resp.headers.get("X-ACF-Free-Tier", "false") == "true"
        _session_spent += amount

        result = {
            "status_code": resp.status_code,
            "amount_charged": amount,
            "free_tier": free_tier,
            "session_total_spent": _session_spent,
        }
        try:
            result["data"] = resp.json()
        except Exception:
            result["data"] = resp.text[:500]

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    elif name == "check_balance":
        balance = _api("GET", f"/api/v1/balance/{BUYER_ID}")
        return [TextContent(type="text", text=json.dumps(balance, indent=2))]

    elif name == "check_budget":
        remaining = BUDGET_LIMIT - _session_spent
        return [TextContent(type="text", text=json.dumps({
            "budget_limit": BUDGET_LIMIT,
            "session_spent": _session_spent,
            "remaining": remaining,
            "buyer_id": BUYER_ID,
        }, indent=2))]

    elif name == "get_recommendations":
        services = _api("GET", "/api/v1/services")
        if isinstance(services, dict) and "error" in services:
            return [TextContent(type="text", text=json.dumps(services))]

        # Sort by free tier (most free calls first), then by price (cheapest first)
        ranked = sorted(
            (services if isinstance(services, list) else []),
            key=lambda s: (-s.get("free_tier_calls", 0), float(s.get("price_per_call", 999))),
        )

        recs = []
        for svc in ranked[:5]:
            recs.append({
                "id": svc["id"],
                "name": svc["name"],
                "price_per_call": svc.get("price_per_call"),
                "free_tier_calls": svc.get("free_tier_calls", 0),
                "reason": "Has free tier" if svc.get("free_tier_calls", 0) > 0 else "Best price",
            })

        return [TextContent(type="text", text=json.dumps(recs, indent=2))]

    return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
