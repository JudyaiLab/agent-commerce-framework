"""Health check, landing page, and SEO endpoints."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from marketplace.i18n import SUPPORTED_LOCALES

router = APIRouter()

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _i18n_ctx(request: Request) -> dict:
    """Build i18n template context from request state (set by middleware)."""
    return {
        "t": getattr(request.state, "t", lambda k: k),
        "locale": getattr(request.state, "locale", "en"),
        "supported_locales": SUPPORTED_LOCALES,
    }

_BASE_URL = "https://agentictrade.io"


# ── SEO Infrastructure (Phase 0) ──────────────────────────────────


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Serve robots.txt — allow public pages, block dashboard and API."""
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /marketplace\n"
        "Allow: /api-docs\n"
        "Allow: /starter-kit\n"
        "Allow: /pricing\n"
        "Allow: /providers\n"
        "Allow: /about\n"
        "Allow: /terms\n"
        "Allow: /privacy\n"
        "Allow: /status\n"
        "Allow: /llms.txt\n"
        "Allow: /.well-known/\n"
        "Disallow: /dashboard/\n"
        "Disallow: /api/\n"
        "Disallow: /docs\n"
        "Disallow: /checkout/\n"
        "\n"
        f"Sitemap: {_BASE_URL}/sitemap.xml\n"
    )


@router.get("/sitemap.xml", response_class=Response)
async def sitemap_xml():
    """Auto-generate sitemap with all public pages."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    pages = [
        {"loc": "/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": "/marketplace", "priority": "0.9", "changefreq": "daily"},
        {"loc": "/api-docs", "priority": "0.8", "changefreq": "weekly"},
        {"loc": "/pricing", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/providers", "priority": "0.8", "changefreq": "monthly"},
        {"loc": "/about", "priority": "0.6", "changefreq": "monthly"},
        {"loc": "/starter-kit", "priority": "0.7", "changefreq": "monthly"},
        {"loc": "/terms", "priority": "0.3", "changefreq": "monthly"},
        {"loc": "/privacy", "priority": "0.3", "changefreq": "monthly"},
        {"loc": "/status", "priority": "0.4", "changefreq": "daily"},
        {"loc": "/llms.txt", "priority": "0.5", "changefreq": "monthly"},
    ]

    urls = []
    for page in pages:
        urls.append(
            f"  <url>\n"
            f"    <loc>{_BASE_URL}{page['loc']}</loc>\n"
            f"    <lastmod>{today}</lastmod>\n"
            f"    <changefreq>{page['changefreq']}</changefreq>\n"
            f"    <priority>{page['priority']}</priority>\n"
            f"  </url>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )

    return Response(content=xml, media_type="application/xml")


@router.get("/llms.txt", response_class=PlainTextResponse)
@router.get("/.well-known/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    """GEO: Tell LLMs what AgenticTrade is. Official llms.txt spec format."""
    return (
        "# AgenticTrade\n"
        "\n"
        "> AgenticTrade is an open-source API marketplace where AI agents autonomously\n"
        "> discover, negotiate, and purchase API services. It provides multi-rail payments\n"
        "> (x402 USDC on Base, PayPal, 300+ cryptocurrencies via NOWPayments), a reputation\n"
        "> engine, MCP bridge for native LLM integration, and a self-service provider portal.\n"
        "> Built with FastAPI, 1500+ tests, MIT license, 9-language i18n. By JudyAI Lab.\n"
        "\n"
        "Key concepts: MCP Tool Descriptor (machine-readable API description), Proxy Key\n"
        "(credential routing through AgenticTrade so provider keys are never exposed),\n"
        "x402 (HTTP-native payment protocol for per-call USDC micropayments on Base).\n"
        "Commission: 0% month 1, 5% months 2-3, 10% from month 4.\n"
        "\n"
        f"## Getting Started\n"
        f"- [Home]({_BASE_URL}/): Platform overview and value proposition\n"
        f"- [Getting Started]({_BASE_URL}/docs/getting-started): Quick start for providers and consumers\n"
        f"- [API Documentation]({_BASE_URL}/api-docs): Interactive API reference with all endpoints\n"
        f"- [Pricing]({_BASE_URL}/pricing): Marketplace fee structure and provider tiers\n"
        "\n"
        f"## For API Providers\n"
        f"- [Provider Guide]({_BASE_URL}/docs/provider-guide): How to list and monetize your API\n"
        f"- [Provider Portal]({_BASE_URL}/portal): Self-service dashboard for managing listings\n"
        f"- [Payments & Settlement]({_BASE_URL}/docs/payments): USDC, PayPal, crypto payout options\n"
        "\n"
        f"## For AI Agents & Developers\n"
        f"- [API Reference]({_BASE_URL}/docs/api-reference): Full endpoint documentation\n"
        f"- [Service Discovery]({_BASE_URL}/marketplace): Browse and compare available APIs\n"
        f"- [Architecture]({_BASE_URL}/docs/architecture): MCP bridge and system design\n"
        "\n"
        f"## Trust & Compliance\n"
        f"- [About]({_BASE_URL}/about): Platform mission and architecture\n"
        f"- [Terms of Service]({_BASE_URL}/terms): Platform terms\n"
        f"- [Privacy Policy]({_BASE_URL}/privacy): Data handling practices\n"
        f"- [Status]({_BASE_URL}/status): Platform operational status\n"
        "\n"
        f"## Optional\n"
        f"- [Starter Kit]({_BASE_URL}/starter-kit): Educational guide to agent commerce\n"
    )


@router.get("/.well-known/ai-plugin.json")
async def ai_plugin_json():
    """OpenAI-compatible plugin manifest for agent discovery."""
    return {
        "schema_version": "v1",
        "name_for_human": "AgenticTrade",
        "name_for_model": "agentictrade",
        "description_for_human": "API marketplace where AI agents discover, call, and pay for services autonomously.",
        "description_for_model": "AgenticTrade is an API marketplace for AI agents. Use it to discover available API services, check pricing, and make API calls with automatic billing. Services include crypto analysis, backtesting, data processing, and more. Agents pay per call in USDC.",
        "auth": {"type": "service_http", "authorization_type": "bearer"},
        "api": {
            "type": "openapi",
            "url": f"{_BASE_URL}/api/v1/openapi.json",
        },
        "logo_url": f"{_BASE_URL}/static/img/logo.webp",
        "contact_email": "hello@judyailab.com",
        "legal_info_url": f"{_BASE_URL}/terms",
    }


@router.get("/.well-known/agents.json")
async def agents_json():
    """ACDP-compatible agent discovery manifest."""
    return {
        "name": "AgenticTrade",
        "description": "API marketplace for autonomous AI agent commerce. Agents discover, call, and pay for API services.",
        "url": _BASE_URL,
        "capabilities": [
            "api_marketplace",
            "service_discovery",
            "mcp_tool_descriptors",
            "x402_payments",
            "paypal_payments",
            "crypto_payments",
            "proxy_key_auth",
            "usage_billing",
        ],
        "protocols": ["mcp", "x402", "http", "openapi"],
        "endpoints": {
            "services": f"{_BASE_URL}/api/v1/services",
            "proxy": f"{_BASE_URL}/api/v1/proxy/{{service_id}}",
            "balance": f"{_BASE_URL}/api/v1/billing/balance",
            "register": f"{_BASE_URL}/portal/register",
            "mcp_registry": f"{_BASE_URL}/api/v1/mcp/registry",
        },
        "pricing": {
            "model": "pay_per_call",
            "currency": "USDC",
            "range": "$0.10 - $2.00 per call",
            "free_tier": "10 free calls per service",
        },
        "contact": "hello@judyailab.com",
    }


@router.get("/.well-known/mcp.json")
async def mcp_json():
    """MCP auto-discovery manifest. Allows MCP clients to find our server."""
    return {
        "version": "1.0",
        "servers": [
            {
                "name": "AgenticTrade Marketplace",
                "description": (
                    "MCP server for AI agent commerce — discover, purchase, "
                    "and consume API services with autonomous payments via "
                    "x402 USDC on Base, PayPal, and 300+ cryptocurrencies."
                ),
                "endpoint": f"{_BASE_URL}/api/v1/mcp",
                "authentication": {
                    "type": "bearer",
                    "description": "Use your AgenticTrade API key as Bearer token",
                },
                "capabilities": [
                    "service-discovery",
                    "api-proxy",
                    "payment-settlement",
                    "reputation-scoring",
                    "provider-management",
                ],
            }
        ],
    }


@router.get("/favicon.ico")
async def favicon():
    """Redirect to static favicon."""
    return RedirectResponse(url="/static/img/favicon.ico", status_code=301)


# ── Public Pages ──────────────────────────────────────────────────


@router.get("/", response_class=HTMLResponse)
async def landing(request: Request):
    """Serve the marketing landing page."""
    db = request.app.state.db

    with db.connect() as conn:
        svc_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM services WHERE status = 'active'"
        ).fetchone()["cnt"]
        total_calls = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_records"
        ).fetchone()["cnt"]
        agent_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM agent_identities"
        ).fetchone()["cnt"]

    return _templates.TemplateResponse("public/landing.html", {
        "request": request,
        "service_count": svc_count,
        "total_calls": total_calls,
        "agent_count": agent_count,
        **_i18n_ctx(request),
    })


@router.get("/marketplace", response_class=HTMLResponse)
async def marketplace(request: Request):
    """Serve the marketplace browser (formerly the landing page)."""
    db = request.app.state.db

    with db.connect() as conn:
        svc_rows = conn.execute(
            "SELECT name, description, price_per_call, free_tier_calls "
            "FROM services WHERE status = 'active' ORDER BY created_at"
        ).fetchall()
        total_calls = conn.execute(
            "SELECT COUNT(*) as cnt FROM usage_records"
        ).fetchone()["cnt"]
        agent_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM agent_identities"
        ).fetchone()["cnt"]

    services = [dict(r) for r in svc_rows]

    return _templates.TemplateResponse("marketplace.html", {
        "request": request,
        "service_count": len(services),
        "total_calls": total_calls,
        "agent_count": agent_count,
        "services": services,
        **_i18n_ctx(request),
    })


@router.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request):
    """Serve the pricing page."""
    db = request.app.state.db

    with db.connect() as conn:
        svc_rows = conn.execute(
            "SELECT name, description, price_per_call, free_tier_calls "
            "FROM services WHERE status = 'active' ORDER BY price_per_call ASC"
        ).fetchall()

    services = [dict(r) for r in svc_rows]

    return _templates.TemplateResponse("public/pricing.html", {
        "request": request,
        "services": services,
        **_i18n_ctx(request),
    })


@router.get("/providers", response_class=HTMLResponse)
async def providers(request: Request):
    """Serve the For Providers page."""
    return _templates.TemplateResponse("public/providers.html", {
        "request": request,
        **_i18n_ctx(request),
    })


@router.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    """Serve the About page."""
    return _templates.TemplateResponse("public/about.html", {
        "request": request,
        **_i18n_ctx(request),
    })


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    """Serve the Terms of Service page."""
    return _templates.TemplateResponse("public/terms.html", {
        "request": request,
        **_i18n_ctx(request),
    })


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    """Serve the Privacy Policy page."""
    return _templates.TemplateResponse("public/privacy.html", {
        "request": request,
        **_i18n_ctx(request),
    })


@router.get("/starter-kit", response_class=HTMLResponse)
async def starter_kit_page(request: Request):
    """Serve the Starter Kit product/sales page."""
    return _templates.TemplateResponse("starter-kit-product.html", {
        "request": request,
        **_i18n_ctx(request),
    })


@router.get("/checkout/success", response_class=HTMLResponse)
async def checkout_success(
    request: Request,
    session_id: str = "",
    payment_id: str = "",
    provider: str = "",
):
    """Post-purchase thank you page."""
    return _templates.TemplateResponse("checkout-success.html", {
        "request": request,
        "session_id": session_id,
        "payment_id": payment_id,
        "provider": provider,
    })


@router.get("/api-docs", response_class=HTMLResponse)
async def api_docs(request: Request):
    """Serve the public API documentation page with live service data."""
    db = request.app.state.db

    with db.connect() as conn:
        svc_rows = conn.execute(
            "SELECT id, name, description, price_per_call, free_tier_calls "
            "FROM services WHERE status = 'active' ORDER BY price_per_call ASC"
        ).fetchall()

    services = [dict(r) for r in svc_rows]

    demo_id = scanner_id = backtest_id = ""
    for svc in services:
        name_lower = svc["name"].lower()
        if "demo" in name_lower:
            demo_id = svc["id"]
        elif "scanner" in name_lower:
            scanner_id = svc["id"]
        elif "backtest" in name_lower:
            backtest_id = svc["id"]

    return _templates.TemplateResponse("api-docs.html", {
        "request": request,
        "services": services,
        "demo_service_id": demo_id,
        "scanner_service_id": scanner_id,
        "backtest_service_id": backtest_id,
        **_i18n_ctx(request),
    })


@router.get("/status", response_class=HTMLResponse)
async def status_page(request: Request):
    """Serve the public platform status page with real-time health metrics."""
    db = getattr(request.app.state, "db", None)

    # ── Database health ──
    db_ok = False
    if db is not None:
        try:
            with db.connect() as conn:
                conn.execute("SELECT 1")
            db_ok = True
        except Exception:
            pass

    # ── Metrics from health_checks table ──
    uptime_pct = 100.0
    avg_latency_ms = 0
    active_services = 0
    daily_status: list[dict] = []

    now = datetime.now(timezone.utc)

    if db is not None and db_ok:
        try:
            with db.connect() as conn:
                # Active services count
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM services WHERE status = 'active'"
                ).fetchone()
                active_services = row["cnt"] if row else 0

                # Check if health_checks table exists
                table_check = conn.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name='health_checks'"
                ).fetchone()

                if table_check:
                    # 30-day uptime and latency from health_checks
                    cutoff_30d = (now - timedelta(days=30)).isoformat()
                    stats = conn.execute(
                        "SELECT COUNT(*) as total, "
                        "SUM(CASE WHEN reachable = 1 THEN 1 ELSE 0 END) as up, "
                        "AVG(CASE WHEN reachable = 1 THEN latency_ms END) as avg_lat "
                        "FROM health_checks WHERE checked_at >= ?",
                        (cutoff_30d,),
                    ).fetchone()

                    if stats and stats["total"] > 0:
                        uptime_pct = round(
                            (stats["up"] or 0) / stats["total"] * 100, 2
                        )
                        avg_latency_ms = round(stats["avg_lat"] or 0)

                    # 7-day daily status
                    for i in range(6, -1, -1):
                        day_start = (now - timedelta(days=i)).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        day_end = day_start + timedelta(days=1)
                        day_row = conn.execute(
                            "SELECT COUNT(*) as total, "
                            "SUM(CASE WHEN reachable = 1 THEN 1 ELSE 0 END) as up "
                            "FROM health_checks "
                            "WHERE checked_at >= ? AND checked_at < ?",
                            (day_start.isoformat(), day_end.isoformat()),
                        ).fetchone()

                        day_date = day_start.strftime("%b %d")
                        if day_row and day_row["total"] > 0:
                            day_uptime = (day_row["up"] or 0) / day_row["total"]
                            if day_uptime >= 0.999:
                                status = "up"
                                label = "Operational"
                            elif day_uptime >= 0.95:
                                status = "degraded"
                                label = "Degraded"
                            else:
                                status = "down"
                                label = "Disruption"
                        else:
                            # No data for this day = assume operational
                            status = "up"
                            label = "No issues"

                        daily_status.append({
                            "date": day_date,
                            "status": status,
                            "label": label,
                        })
                else:
                    # No health_checks table yet — show default 7 green days
                    for i in range(6, -1, -1):
                        day_start = now - timedelta(days=i)
                        daily_status.append({
                            "date": day_start.strftime("%b %d"),
                            "status": "up",
                            "label": "No issues",
                        })
        except Exception:
            # Fallback if any query fails
            for i in range(6, -1, -1):
                day_start = now - timedelta(days=i)
                daily_status.append({
                    "date": day_start.strftime("%b %d"),
                    "status": "up",
                    "label": "No issues",
                })

    # Fill daily_status if empty
    if not daily_status:
        for i in range(6, -1, -1):
            day_start = now - timedelta(days=i)
            daily_status.append({
                "date": day_start.strftime("%b %d"),
                "status": "up",
                "label": "No issues",
            })

    # Determine overall platform status
    if not db_ok:
        platform_status = "degraded"
    elif uptime_pct >= 99.9:
        platform_status = "operational"
    elif uptime_pct >= 95.0:
        platform_status = "degraded"
    else:
        platform_status = "down"

    updated_at = now.strftime("%Y-%m-%d %H:%M UTC")

    return _templates.TemplateResponse("public/status.html", {
        "request": request,
        "platform_status": platform_status,
        "uptime_pct": uptime_pct,
        "avg_latency_ms": avg_latency_ms,
        "active_services": active_services,
        "daily_status": daily_status,
        "db_ok": db_ok,
        "updated_at": updated_at,
        **_i18n_ctx(request),
    })


@router.get("/health")
async def health(request: Request):
    """Lightweight health check with basic dependency verification."""
    db = getattr(request.app.state, "db", None)
    db_ok = False
    if db is not None:
        try:
            with db.connect() as conn:
                conn.execute("SELECT 1")
            db_ok = True
        except Exception:
            pass
    status = "ok" if db_ok else "degraded"
    return {"status": status, "database": "ok" if db_ok else "error"}


@router.get("/health/details")
async def health_details(request: Request):
    """Full health details — admin-only."""
    from api.deps import require_admin
    require_admin(request)  # Raises HTTPException(401/403) if not admin

    db = getattr(request.app.state, "db", None)
    checks: dict = {}
    db_status = "not_configured"
    db_latency = None
    if db is not None:
        import time as _time
        t0 = _time.monotonic()
        db_detail = None
        try:
            with db.connect() as conn:
                conn.execute("SELECT 1")
            db_latency = round((_time.monotonic() - t0) * 1000, 1)
            db_status = "ok"
        except Exception as exc:
            db_latency = round((_time.monotonic() - t0) * 1000, 1)
            db_status = "error"
            db_detail = str(exc)
    db_entry: dict = {"status": db_status, "latency_ms": db_latency}
    if db_detail:
        db_entry["detail"] = db_detail
    checks["database"] = db_entry

    registry = getattr(request.app.state, "registry", None)
    services_count = 0
    if registry is not None:
        try:
            services_count = len(registry.list_services())
        except Exception:
            pass
    checks["services_count"] = services_count

    payment_router = getattr(request.app.state, "payment_router", None)
    payment_providers: list[str] = []
    if payment_router is not None:
        providers_dict = getattr(payment_router, "_providers", {})
        payment_providers = list(providers_dict.keys())
    checks["payment_providers"] = payment_providers

    overall = "ok" if db_status == "ok" else "degraded"
    from fastapi.responses import JSONResponse as _JSONResp
    status_code = 200 if overall == "ok" else 503
    return _JSONResp(
        content={
            "status": overall,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        },
        status_code=status_code,
    )
