"""
Provider Portal — web UI for human providers to manage their API business.

Routes:
  GET  /portal/login      — login page
  POST /portal/login      — handle login
  GET  /portal/register   — registration page
  POST /portal/register   — handle registration
  GET  /portal/dashboard  — provider dashboard (protected)
  GET  /portal/services   — manage services (protected)
  GET  /portal/analytics  — revenue analytics (protected)
  GET  /portal/settings   — account settings (protected)
  POST /portal/settings   — update settings (protected)
  GET  /portal/logout     — logout
  GET  /portal/verify     — email verification callback
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from marketplace.provider_auth import (
    _SESSION_COOKIE,
    authenticate,
    create_account,
    create_pat_record,
    delete_pat_record,
    ensure_provider_accounts_table,
    get_account_by_id,
    link_api_key,
    sign_session,
    update_profile,
    validate_pat_expiry,
    verify_email,
    verify_session,
    ProviderAccountError,
)
from marketplace.auth import generate_api_key, hash_secret
from marketplace.i18n import detect_locale, make_translator, SUPPORTED_LOCALES
from datetime import datetime, timezone
import hashlib
import hmac
import secrets
import os

from marketplace.rate_limit import DatabaseRateLimiter

logger = logging.getLogger("acf.portal")

# --- Portal brute-force protection (DB-backed, works across workers) ---
_PORTAL_FAIL_MAX = 5
_PORTAL_FAIL_WINDOW = 60.0  # seconds
_portal_limiter: DatabaseRateLimiter | None = None


def _get_portal_limiter(db) -> DatabaseRateLimiter:
    """Lazy-init a shared DB-backed rate limiter for portal login attempts."""
    global _portal_limiter
    if _portal_limiter is None:
        _portal_limiter = DatabaseRateLimiter(
            db, rate=_PORTAL_FAIL_MAX, window_seconds=_PORTAL_FAIL_WINDOW,
        )
    return _portal_limiter


def _check_portal_brute_force(db, client_ip: str) -> bool:
    """Return True if IP has exceeded portal login failure limit."""
    limiter = _get_portal_limiter(db)
    return not limiter.allow(f"portal_login:{client_ip}")

router = APIRouter(prefix="/portal", tags=["portal"])

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_provider(request: Request) -> dict | None:
    """Extract provider account from session cookie. Returns None if not logged in."""
    token = request.cookies.get(_SESSION_COOKIE, "")
    if not token:
        return None
    provider_id = verify_session(token)
    if not provider_id:
        return None
    db = request.app.state.db
    return get_account_by_id(db, provider_id)


def _require_provider(request: Request) -> dict:
    """Require authenticated provider. Raises redirect to login."""
    provider = _get_provider(request)
    if provider is None:
        raise HTTPException(status_code=303, headers={"Location": "/portal/login"})
    return provider


# Derive separate keys from the master secret using HMAC prefix derivation
# so that session signing and CSRF protection never share the same raw key.
_RAW_PORTAL_SECRET = os.environ.get("ACF_SECRET_KEY") or os.urandom(32).hex()
_CSRF_SECRET = hmac.new(
    _RAW_PORTAL_SECRET.encode(), b"portal_csrf", hashlib.sha256,
).hexdigest()


def _csrf_token(session_cookie: str) -> str:
    """Generate CSRF token from session cookie using HMAC."""
    nonce = secrets.token_hex(8)
    sig = hmac.new(
        _CSRF_SECRET.encode(), f"{session_cookie}:{nonce}".encode(), hashlib.sha256,
    ).hexdigest()[:32]
    return f"{nonce}:{sig}"


def _verify_csrf(session_cookie: str, token: str) -> bool:
    """Verify CSRF token against session cookie."""
    if not token or ":" not in token:
        return False
    nonce, sig = token.split(":", 1)
    expected = hmac.new(
        _CSRF_SECRET.encode(), f"{session_cookie}:{nonce}".encode(), hashlib.sha256,
    ).hexdigest()[:32]
    return hmac.compare_digest(sig, expected)


def _locale_context(request: Request) -> dict:
    """Build locale context for templates."""
    locale = detect_locale(
        query_lang=request.query_params.get("lang"),
        cookie_lang=request.cookies.get("lang"),
        accept_language=request.headers.get("accept-language"),
    )
    t = make_translator(locale)
    return {"t": t, "locale": locale, "supported_locales": SUPPORTED_LOCALES}


def _provider_stats(db, owner_id: str) -> dict:
    """Query provider stats for dashboard."""
    with db.connect() as conn:
        svc_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM services WHERE provider_id = ? AND status = 'active'",
            (owner_id,),
        ).fetchone()["cnt"]

        calls = conn.execute(
            "SELECT COUNT(*) as cnt, COALESCE(SUM(amount_usd), 0) as revenue FROM usage_records WHERE provider_id = ?",
            (owner_id,),
        ).fetchone()

        settlements = conn.execute(
            "SELECT COALESCE(SUM(net_amount), 0) as total_settled FROM settlements WHERE provider_id = ? AND status = 'completed'",
            (owner_id,),
        ).fetchone()

        services = conn.execute(
            """SELECT s.id, s.name, s.endpoint, s.price_per_call, s.status, s.created_at,
                      COUNT(u.id) as call_count, COALESCE(SUM(u.amount_usd), 0) as revenue
               FROM services s
               LEFT JOIN usage_records u ON u.service_id = s.id
               WHERE s.provider_id = ?
               GROUP BY s.id
               ORDER BY revenue DESC""",
            (owner_id,),
        ).fetchall()

    return {
        "service_count": svc_count,
        "total_calls": calls["cnt"],
        "total_revenue": round(calls["revenue"], 2),
        "total_settled": round(settlements["total_settled"], 2),
        "pending_settlement": round(calls["revenue"] - settlements["total_settled"], 2),
        "services": [dict(r) for r in services],
    }


# ---------------------------------------------------------------------------
# Public routes (no auth required)
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login page."""
    if _get_provider(request):
        return RedirectResponse("/portal/dashboard", status_code=303)
    ctx = _locale_context(request)
    session = request.cookies.get(_SESSION_COOKIE, "anon")
    return templates.TemplateResponse("portal/login.html", {
        "request": request, **ctx, "error": None,
        "csrf_token": _csrf_token(session),
    })


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(""),
):
    """Handle login form submission."""
    client_ip = request.client.host if request.client else "unknown"
    session = request.cookies.get(_SESSION_COOKIE, "anon")
    db = request.app.state.db

    # Brute-force protection: DB-backed, works across all workers
    if _check_portal_brute_force(db, client_ip):
        ctx = _locale_context(request)
        return templates.TemplateResponse("portal/login.html", {
            "request": request, **ctx,
            "error": "Too many failed attempts. Please try again later.",
            "csrf_token": _csrf_token(session),
        }, status_code=429)

    if not _verify_csrf(session, csrf_token):
        ctx = _locale_context(request)
        return templates.TemplateResponse("portal/login.html", {
            "request": request, **ctx, "error": "Invalid request. Please try again.",
            "csrf_token": _csrf_token(session),
        }, status_code=403)
    ensure_provider_accounts_table(db)
    account = authenticate(db, email, password)
    ctx = _locale_context(request)

    if account is None:
        return templates.TemplateResponse("portal/login.html", {
            "request": request, **ctx,
            "error": "Invalid email or password",
            "csrf_token": _csrf_token(session),
        }, status_code=401)

    # Set session cookie and redirect to dashboard
    token = sign_session(account["id"])
    response = RedirectResponse("/portal/dashboard", status_code=303)
    response.set_cookie(
        _SESSION_COOKIE, token,
        max_age=3600 * 24, httponly=True, secure=True, samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Render registration page."""
    if _get_provider(request):
        return RedirectResponse("/portal/dashboard", status_code=303)
    ctx = _locale_context(request)
    session = request.cookies.get(_SESSION_COOKIE, "anon")
    return templates.TemplateResponse("portal/register.html", {
        "request": request, **ctx, "error": None, "success": False,
        "csrf_token": _csrf_token(session),
    })


@router.post("/register", response_class=HTMLResponse)
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    display_name: str = Form(""),
    csrf_token: str = Form(""),
):
    """Handle registration form submission."""
    session = request.cookies.get(_SESSION_COOKIE, "anon")
    ctx = _locale_context(request)
    if not _verify_csrf(session, csrf_token):
        return templates.TemplateResponse("portal/register.html", {
            "request": request, **ctx,
            "error": "Invalid request. Please try again.", "success": False,
            "csrf_token": _csrf_token(session),
        }, status_code=403)
    db = request.app.state.db
    ensure_provider_accounts_table(db)

    if password != confirm_password:
        return templates.TemplateResponse("portal/register.html", {
            "request": request, **ctx,
            "error": "Passwords do not match", "success": False,
            "csrf_token": _csrf_token(session),
        }, status_code=400)

    try:
        locale = ctx["locale"]
        account = create_account(db, email, password, display_name, locale)
    except ProviderAccountError as e:
        return templates.TemplateResponse("portal/register.html", {
            "request": request, **ctx,
            "error": str(e), "success": False,
            "csrf_token": _csrf_token(session),
        }, status_code=400)

    # Auto-generate an API key for the provider
    key_id, raw_secret = generate_api_key(prefix="acf")
    hashed = hash_secret(raw_secret)
    now = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO api_keys (key_id, hashed_secret, owner_id, role, created_at)
               VALUES (?, ?, ?, 'provider', ?)""",
            (key_id, hashed, account["id"], now),
        )
    link_api_key(db, account["id"], key_id)

    # Log in automatically
    token = sign_session(account["id"])
    response = RedirectResponse("/portal/dashboard", status_code=303)
    response.set_cookie(
        _SESSION_COOKIE, token,
        max_age=3600 * 24, httponly=True, secure=True, samesite="lax",
    )
    return response


@router.get("/verify", response_class=HTMLResponse)
async def verify_email_callback(request: Request, token: str = ""):
    """Email verification callback."""
    db = request.app.state.db
    ensure_provider_accounts_table(db)
    success = verify_email(db, token) if token else False
    ctx = _locale_context(request)
    return templates.TemplateResponse("portal/verify.html", {
        "request": request, **ctx, "success": success,
    })


@router.get("/logout")
async def logout(request: Request):
    """Logout — clear session cookie."""
    response = RedirectResponse("/portal/login", status_code=303)
    response.delete_cookie(_SESSION_COOKIE)
    return response


# ---------------------------------------------------------------------------
# Protected routes (require login)
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_class=HTMLResponse)
async def portal_dashboard(request: Request):
    """Provider dashboard — overview stats."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    db = request.app.state.db
    stats = _provider_stats(db, provider["id"])
    ctx = _locale_context(request)
    return templates.TemplateResponse("portal/dashboard.html", {
        "request": request, **ctx,
        "provider": provider, "stats": stats,
    })


@router.get("/services", response_class=HTMLResponse)
async def portal_services(request: Request):
    """Service management page."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    db = request.app.state.db
    stats = _provider_stats(db, provider["id"])
    ctx = _locale_context(request)
    return templates.TemplateResponse("portal/services.html", {
        "request": request, **ctx,
        "provider": provider, "services": stats["services"],
    })


@router.get("/analytics", response_class=HTMLResponse)
async def portal_analytics(request: Request):
    """Revenue analytics page."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    db = request.app.state.db
    stats = _provider_stats(db, provider["id"])

    # Commission info — use CommissionEngine so rates stay in sync with platform config
    commission_engine = getattr(request.app.state, "commission_engine", None)
    provider_api_key_id = provider.get("api_key_id") or provider.get("id")
    if commission_engine is not None:
        commission_info = commission_engine.get_provider_commission_info(provider_api_key_id)
        raw_rate = commission_info.get("current_rate", 0)
        # Convert Decimal to a plain float percentage (0.05 → 5.0)
        try:
            commission_rate = float(raw_rate) * 100
        except (TypeError, ValueError):
            commission_rate = 10.0
        tier_name = commission_info.get("current_tier", "standard")
        month_number = commission_info.get("month_number") or 1
        months_active = month_number
        _tier_labels = {
            "free_trial": f"Launch ({commission_rate:.0f}%)",
            "growth": f"Growth ({commission_rate:.0f}%)",
            "founding_seller": f"Founding Seller ({commission_rate:.0f}%)",
        }
        commission_tier = _tier_labels.get(tier_name, f"Standard ({commission_rate:.0f}%)")
    else:
        # Fallback: derive from account creation date if engine not available
        from datetime import datetime, timezone
        created = provider.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created)
            months_active = max(1, (datetime.now(timezone.utc) - created_dt).days // 30)
        except (ValueError, TypeError):
            months_active = 1
        if months_active <= 1:
            commission_rate = 0.0
            commission_tier = "Launch (0%)"
        elif months_active <= 3:
            commission_rate = 5.0
            commission_tier = "Growth (5%)"
        else:
            commission_rate = 10.0
            commission_tier = "Standard (10%)"

    ctx = _locale_context(request)
    return templates.TemplateResponse("portal/analytics.html", {
        "request": request, **ctx,
        "provider": provider, "stats": stats,
        "commission_rate": commission_rate,
        "commission_tier": commission_tier,
        "months_active": months_active,
    })


@router.get("/settings", response_class=HTMLResponse)
async def portal_settings(request: Request):
    """Account settings page."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    ctx = _locale_context(request)
    session = request.cookies.get(_SESSION_COOKIE, "")
    db = request.app.state.db

    # Check for existing PAT token
    pat_info = _get_pat_info(db, provider)

    return templates.TemplateResponse("portal/settings.html", {
        "request": request, **ctx,
        "provider": provider, "success": None, "error": None,
        "csrf_token": _csrf_token(session),
        "has_pat": pat_info is not None,
        "pat_key_id": pat_info["key_id"] if pat_info else None,
        "pat_created": pat_info["created_at"][:10] if pat_info else None,
        "new_token": None,
    })


@router.post("/settings", response_class=HTMLResponse)
async def portal_settings_update(
    request: Request,
    display_name: str = Form(""),
    company_name: str = Form(""),
    csrf_token: str = Form(""),
):
    """Update account settings."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    session = request.cookies.get(_SESSION_COOKIE, "")
    ctx = _locale_context(request)
    if not _verify_csrf(session, csrf_token):
        return templates.TemplateResponse("portal/settings.html", {
            "request": request, **ctx,
            "provider": provider, "success": None,
            "error": "Invalid request. Please try again.",
            "csrf_token": _csrf_token(session),
            "has_pat": False, "pat_key_id": None, "pat_created": None, "new_token": None,
        }, status_code=403)
    db = request.app.state.db
    update_profile(db, provider["id"], display_name=display_name, company_name=company_name)
    provider = get_account_by_id(db, provider["id"])
    pat_info = _get_pat_info(db, provider)
    return templates.TemplateResponse("portal/settings.html", {
        "request": request, **ctx,
        "provider": provider, "success": "Settings updated", "error": None,
        "csrf_token": _csrf_token(session),
        "has_pat": pat_info is not None,
        "pat_key_id": pat_info["key_id"] if pat_info else None,
        "pat_created": pat_info["created_at"][:10] if pat_info else None,
        "new_token": None,
    })


# ---------------------------------------------------------------------------
# PAT (Personal API Token) helpers & routes
# ---------------------------------------------------------------------------

def _get_pat_info(db, provider: dict) -> dict | None:
    """Find an existing PAT token (pat_ prefix) for this provider."""
    owner_id = provider.get("api_key_id")
    if not owner_id:
        return None
    # owner_id in api_keys matches the provider's account id
    with db.connect() as conn:
        row = conn.execute(
            "SELECT key_id, created_at FROM api_keys WHERE owner_id = ? AND key_id LIKE 'pat_%'",
            (provider["id"],),
        ).fetchone()
    return dict(row) if row else None


@router.post("/api-token", response_class=HTMLResponse)
async def generate_api_token(request: Request, csrf_token: str = Form("")):
    """Generate a PAT token for AI assistant access."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    session = request.cookies.get(_SESSION_COOKIE, "")
    ctx = _locale_context(request)
    db = request.app.state.db

    if not _verify_csrf(session, csrf_token):
        pat_info = _get_pat_info(db, provider)
        return templates.TemplateResponse("portal/settings.html", {
            "request": request, **ctx,
            "provider": provider, "success": None,
            "error": "Invalid request. Please try again.",
            "csrf_token": _csrf_token(session),
            "has_pat": pat_info is not None,
            "pat_key_id": pat_info["key_id"] if pat_info else None,
            "pat_created": pat_info["created_at"][:10] if pat_info else None,
            "new_token": None,
        }, status_code=403)

    # Check for existing PAT
    existing = _get_pat_info(db, provider)
    if existing:
        return templates.TemplateResponse("portal/settings.html", {
            "request": request, **ctx,
            "provider": provider, "success": None,
            "error": "You already have an API token. Revoke it first to generate a new one.",
            "csrf_token": _csrf_token(session),
            "has_pat": True,
            "pat_key_id": existing["key_id"],
            "pat_created": existing["created_at"][:10],
            "new_token": None,
        }, status_code=400)

    # Generate PAT using the same mechanism as registration keys
    key_id, raw_secret = generate_api_key(prefix="pat")
    hashed = hash_secret(raw_secret)
    now = datetime.now(timezone.utc).isoformat()
    with db.connect() as conn:
        conn.execute(
            """INSERT INTO api_keys (key_id, hashed_secret, owner_id, role, created_at)
               VALUES (?, ?, ?, 'provider', ?)""",
            (key_id, hashed, provider["id"], now),
        )

    # Create PAT expiry record (default 90 days)
    create_pat_record(db, key_id, provider["id"])

    new_token = f"{key_id}:{raw_secret}"
    logger.info("PAT generated for provider %s: %s", provider["id"], key_id)

    return templates.TemplateResponse("portal/settings.html", {
        "request": request, **ctx,
        "provider": provider, "success": "API token generated successfully.",
        "error": None,
        "csrf_token": _csrf_token(session),
        "has_pat": True,
        "pat_key_id": key_id,
        "pat_created": now[:10],
        "new_token": new_token,
    })


@router.post("/revoke-api-token", response_class=HTMLResponse)
async def revoke_api_token(request: Request, csrf_token: str = Form("")):
    """Revoke the provider's PAT token."""
    provider = _get_provider(request)
    if not provider:
        return RedirectResponse("/portal/login", status_code=303)
    session = request.cookies.get(_SESSION_COOKIE, "")
    ctx = _locale_context(request)
    db = request.app.state.db

    if not _verify_csrf(session, csrf_token):
        pat_info = _get_pat_info(db, provider)
        return templates.TemplateResponse("portal/settings.html", {
            "request": request, **ctx,
            "provider": provider, "success": None,
            "error": "Invalid request. Please try again.",
            "csrf_token": _csrf_token(session),
            "has_pat": pat_info is not None,
            "pat_key_id": pat_info["key_id"] if pat_info else None,
            "pat_created": pat_info["created_at"][:10] if pat_info else None,
            "new_token": None,
        }, status_code=403)

    # Delete all PAT keys and their expiry records for this provider
    with db.connect() as conn:
        pat_rows = conn.execute(
            "SELECT key_id FROM api_keys WHERE owner_id = ? AND key_id LIKE 'pat_%'",
            (provider["id"],),
        ).fetchall()
        conn.execute(
            "DELETE FROM api_keys WHERE owner_id = ? AND key_id LIKE 'pat_%'",
            (provider["id"],),
        )
    for row in pat_rows:
        delete_pat_record(db, row["key_id"])

    logger.info("PAT revoked for provider %s", provider["id"])

    return templates.TemplateResponse("portal/settings.html", {
        "request": request, **ctx,
        "provider": provider, "success": "API token revoked.",
        "error": None,
        "csrf_token": _csrf_token(session),
        "has_pat": False, "pat_key_id": None, "pat_created": None, "new_token": None,
    })
