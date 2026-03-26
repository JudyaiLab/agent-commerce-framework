"""
Billing routes — buyer balance, deposits, and payment webhooks.

Pre-paid credit system:
  1. Buyer creates deposit → gets NOWPayments checkout URL
  2. Buyer pays via NOWPayments
  3. NOWPayments sends IPN callback → balance credited
  4. Buyer calls APIs → balance deducted per call
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from api.deps import extract_owner
from marketplace.db import Database
from marketplace.rate_limit import RateLimiter

logger = logging.getLogger("billing")

router = APIRouter(prefix="/api/v1", tags=["billing"])

NOWPAYMENTS_IPN_SECRET = os.environ.get("NOWPAYMENTS_IPN_SECRET", "")

# IPN rate limiter: 30 requests per minute per source IP (generous for legit payment callbacks)
_ipn_limiter = RateLimiter(rate=30, per=60.0, burst=30)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, le=10000, description="Amount in USDC (min $20 for crypto)")


    buyer_id: str = Field(..., min_length=1, description="Buyer ID")


class DepositResponse(BaseModel):
    deposit_id: str
    amount: float
    status: str
    checkout_url: str | None = None
    message: str


class BalanceResponse(BaseModel):
    buyer_id: str
    balance: float
    total_deposited: float
    total_spent: float


# ---------------------------------------------------------------------------
# Balance endpoints
# ---------------------------------------------------------------------------

@router.get("/balance/{buyer_id}", response_model=BalanceResponse)
def get_balance(buyer_id: str, request: Request):
    """Get buyer's current balance. Requires authentication."""
    owner_id, _ = extract_owner(request)
    if owner_id != buyer_id:
        raise HTTPException(403, "Access denied — can only view own balance")

    db = request.app.state.db

    with db.connect() as conn:
        row = conn.execute(
            "SELECT * FROM balances WHERE buyer_id = ?", (buyer_id,)
        ).fetchone()

    if not row:
        return BalanceResponse(
            buyer_id=buyer_id, balance=0, total_deposited=0, total_spent=0,
        )

    return BalanceResponse(
        buyer_id=buyer_id,
        balance=float(row["balance"]),
        total_deposited=float(row["total_deposited"]),
        total_spent=float(row["total_spent"]),
    )


@router.post("/deposits", response_model=DepositResponse)
async def create_deposit(req: DepositRequest, request: Request):
    """
    Create a deposit to add funds to buyer balance.
    Returns a NOWPayments checkout URL for payment.
    Requires authentication — buyer can only deposit to own account.
    """
    from api.deps import extract_owner
    owner_id, _ = extract_owner(request)
    if owner_id != req.buyer_id:
        raise HTTPException(status_code=403, detail="Can only create deposits for your own account")

    db = request.app.state.db
    deposit_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create NOWPayments invoice
    checkout_url = None
    payment_id = None
    nowpayments_key = os.environ.get("NOWPAYMENTS_API_KEY", "")

    if nowpayments_key:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.nowpayments.io/v1/payment",
                    headers={
                        "x-api-key": nowpayments_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "price_amount": req.amount,
                        "price_currency": "usd",
                        "pay_currency": "usdttrc20",
                        "order_id": deposit_id,
                        "order_description": f"ACF Deposit: ${req.amount} (order {deposit_id[:8]})",
                        "ipn_callback_url": "https://agentictrade.io/api/v1/ipn/nowpayments",
                    },
                )
                if resp.status_code == 201:
                    data = resp.json()
                    payment_id = str(data.get("payment_id", ""))
                    # Build checkout URL
                    checkout_url = f"https://nowpayments.io/payment/?iid={payment_id}"
                    logger.info(
                        "NOWPayments invoice created: %s for $%s (deposit %s)",
                        payment_id, req.amount, deposit_id,
                    )
                else:
                    logger.warning(
                        "NOWPayments API error %d: %s", resp.status_code, resp.text[:200],
                    )
        except Exception as e:
            logger.error("NOWPayments request failed: %s", e)

    # Record deposit (pending until IPN confirms)
    db.insert_deposit({
        "id": deposit_id,
        "buyer_id": req.buyer_id,
        "amount": req.amount,
        "currency": "USDC",
        "payment_provider": "nowpayments",
        "payment_id": payment_id,
        "payment_status": "pending",
        "created_at": now,
    })

    if checkout_url:
        return DepositResponse(
            deposit_id=deposit_id,
            amount=req.amount,
            status="pending",
            checkout_url=checkout_url,
            message=f"Pay ${req.amount} at the checkout URL. Balance will be credited after confirmation.",
        )

    # Fallback: manual deposit (for testing or when NOWPayments unavailable)
    return DepositResponse(
        deposit_id=deposit_id,
        amount=req.amount,
        status="pending",
        message="Deposit created. Send USDT to complete payment.",
    )


# ---------------------------------------------------------------------------
# Admin: manual credit (for testing)
# ---------------------------------------------------------------------------

@router.post("/admin/credit")
def admin_credit_balance(buyer_id: str, amount: float, request: Request):
    """Admin endpoint to manually credit a buyer's balance (for testing)."""
    expected = os.environ.get("ACF_ADMIN_SECRET", "")
    if not expected:
        raise HTTPException(503, "Admin credentials not configured")

    auth_header = request.headers.get("x-admin-key", "")
    if not auth_header:
        raise HTTPException(401, "Admin key required")
    if not hmac.compare_digest(auth_header, expected):
        raise HTTPException(401, "Invalid admin key")

    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    if amount > 10000:
        raise HTTPException(400, "Amount exceeds maximum (10000)")

    db = request.app.state.db
    new_balance = db.credit_balance(buyer_id, Decimal(str(amount)))
    return {
        "buyer_id": buyer_id,
        "credited": amount,
        "new_balance": float(new_balance),
    }


# ---------------------------------------------------------------------------
# NOWPayments IPN callback
# ---------------------------------------------------------------------------

@router.post("/ipn/nowpayments")
async def nowpayments_ipn(request: Request):
    """
    Receive IPN (Instant Payment Notification) from NOWPayments.
    Verifies HMAC signature, then credits buyer balance.
    """
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    if not _ipn_limiter.allow(f"ipn:nowpay:{client_ip}"):
        raise HTTPException(429, "Too many requests")

    body = await request.body()

    # Verify IPN signature — reject if secret not configured
    if not NOWPAYMENTS_IPN_SECRET:
        logger.error("NOWPAYMENTS_IPN_SECRET not configured — rejecting IPN")
        raise HTTPException(503, "IPN verification not configured")

    signature = request.headers.get("x-nowpayments-sig", "")
    if not signature:
        raise HTTPException(400, "Missing signature header")

    try:
        payload = json.loads(body)
        # NOWPayments IPN: sort keys, then HMAC-SHA512
        sorted_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        expected_sig = hmac.new(
            NOWPAYMENTS_IPN_SECRET.encode(),
            sorted_payload.encode(),
            hashlib.sha512,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            logger.warning("IPN signature mismatch")
            raise HTTPException(400, "Invalid signature")
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON body")

    # Extract payment info
    payment_id = str(payload.get("payment_id", ""))
    payment_status = payload.get("payment_status", "")
    order_id = payload.get("order_id", "")

    logger.info(
        "IPN received: payment_id=%s status=%s order_id=%s",
        payment_id, payment_status, order_id,
    )

    # Only process confirmed/finished payments
    confirmed_statuses = {"finished", "confirmed", "sending", "partially_paid"}
    if payment_status not in confirmed_statuses:
        logger.info("IPN status '%s' not confirmed, skipping", payment_status)
        return {"status": "ok", "action": "ignored"}

    # --- Product purchase (order_id starts with "product-") ---
    if order_id.startswith("product-"):
        logger.info(
            "Product purchase confirmed: order_id=%s payment_id=%s",
            order_id, payment_id,
        )
        # Product purchases are fulfilled via download link on success page.
        # IPN just logs the confirmed payment for records.
        return {
            "status": "ok",
            "action": "product_purchase_confirmed",
            "order_id": order_id,
        }

    # --- Balance deposit ---
    db = request.app.state.db

    deposit = db.confirm_deposit(payment_id)
    if not deposit:
        # Try by order_id (deposit_id)
        with db.connect() as conn:
            row = conn.execute(
                "SELECT * FROM deposits WHERE id = ? AND payment_status = 'pending'",
                (order_id,),
            ).fetchone()
            if row:
                deposit = dict(row)
                now = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE deposits SET payment_status = 'confirmed', confirmed_at = ? WHERE id = ?",
                    (now, deposit["id"]),
                )

    if not deposit:
        logger.warning("No pending deposit found for payment_id=%s order_id=%s", payment_id, order_id)
        return {"status": "ok", "action": "no_matching_deposit"}

    amount = Decimal(str(deposit["amount"]))
    new_balance = db.credit_balance(deposit["buyer_id"], amount)

    logger.info(
        "Deposit confirmed: $%s credited to %s (new balance: $%s)",
        amount, deposit["buyer_id"], new_balance,
    )

    return {
        "status": "ok",
        "action": "balance_credited",
        "buyer_id": deposit["buyer_id"],
        "amount": float(amount),
        "new_balance": float(new_balance),
    }


# ---------------------------------------------------------------------------
# PayPal webhook callback
# ---------------------------------------------------------------------------

PAYPAL_WEBHOOK_ID = os.environ.get("PAYPAL_WEBHOOK_ID", "")


@router.post("/ipn/paypal")
async def paypal_webhook(request: Request):
    """
    Receive PayPal CHECKOUT.ORDER.APPROVED / PAYMENT.CAPTURE.COMPLETED webhook.
    Verifies via PayPal API, then credits buyer balance.
    """
    client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown").split(",")[0].strip()
    if not _ipn_limiter.allow(f"ipn:paypal:{client_ip}"):
        raise HTTPException(429, "Too many requests")

    body = await request.body()

    if not PAYPAL_WEBHOOK_ID:
        logger.error("PAYPAL_WEBHOOK_ID not configured — rejecting webhook")
        raise HTTPException(503, "Webhook verification not configured")

    # Verify webhook signature via PayPal API
    import json as _json
    try:
        import httpx as _httpx
        verify_body = {
            "auth_algo": request.headers.get("paypal-auth-algo", ""),
            "cert_url": request.headers.get("paypal-cert-url", ""),
            "transmission_id": request.headers.get("paypal-transmission-id", ""),
            "transmission_sig": request.headers.get("paypal-transmission-sig", ""),
            "transmission_time": request.headers.get("paypal-transmission-time", ""),
            "webhook_id": PAYPAL_WEBHOOK_ID,
            "webhook_event": _json.loads(body),
        }
        paypal_mode = os.environ.get("PAYPAL_MODE", "sandbox")
        base = "https://api-m.paypal.com" if paypal_mode == "live" else "https://api-m.sandbox.paypal.com"
        client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
        client_secret = os.environ.get("PAYPAL_CLIENT_SECRET", "")

        token_resp = _httpx.post(
            f"{base}/v1/oauth2/token",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            timeout=15.0,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        verify_resp = _httpx.post(
            f"{base}/v1/notifications/verify-webhook-signature",
            json=verify_body,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
            timeout=15.0,
        )
        verify_resp.raise_for_status()
        verification = verify_resp.json().get("verification_status", "")
        if verification != "SUCCESS":
            logger.warning("PayPal webhook verification failed: %s", verification)
            raise HTTPException(400, "Invalid signature")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("PayPal webhook verification error: %s", e)
        raise HTTPException(400, "Webhook verification failed")

    event = _json.loads(body)
    event_type = event.get("event_type", "")

    if event_type not in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        logger.info("PayPal webhook: ignoring event type '%s'", event_type)
        return {"status": "ok", "action": "ignored"}

    resource = event.get("resource", {})

    if event_type == "PAYMENT.CAPTURE.COMPLETED":
        amount_str = resource.get("amount", {}).get("value", "0")
        buyer_id = resource.get("custom_id", "") or resource.get("invoice_id", "")
    else:
        # CHECKOUT.ORDER.APPROVED
        purchase_units = resource.get("purchase_units", [{}])
        amount_str = purchase_units[0].get("amount", {}).get("value", "0") if purchase_units else "0"
        buyer_id = purchase_units[0].get("reference_id", "") if purchase_units else ""

    if not buyer_id:
        logger.warning("PayPal webhook: no buyer_id in event")
        return {"status": "ok", "action": "no_buyer_id"}

    amount_usd = Decimal(amount_str)

    db = request.app.state.db
    new_balance = db.credit_balance(buyer_id, amount_usd)

    logger.info(
        "PayPal deposit confirmed: $%s credited to %s (new balance: $%s)",
        amount_usd, buyer_id, new_balance,
    )

    return {
        "status": "ok",
        "action": "balance_credited",
        "buyer_id": buyer_id,
        "amount": float(amount_usd),
        "new_balance": float(new_balance),
    }


# ---------------------------------------------------------------------------
# Product checkout (Starter Kit)
# ---------------------------------------------------------------------------

PAYPAL_CLIENT_ID_CHECKOUT = os.environ.get("PAYPAL_CLIENT_ID", "")

PRODUCTS = {
    "starter-kit": {
        "name": "AgenticTrade Starter Kit",
        "description": "Build an AI agent marketplace — 4 templates, 13-chapter guide, deploy configs, CLI tools",
        "price_cents": 0,  # Free — revenue from 10% platform commission
        "currency": "usd",
        "free": True,
    },
}


@router.get("/checkout/{product_id}")
async def product_checkout(product_id: str, request: Request):
    """Redirect to free download (Starter Kit is free — revenue from platform commission)."""
    product = PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(404, f"Product not found: {product_id}")

    from fastapi.responses import RedirectResponse

    # Free products redirect directly to download
    if product.get("free"):
        base_url = str(request.base_url).rstrip("/")
        return RedirectResponse(
            url=f"{base_url}/api/v1/download/{product_id}",
            status_code=303,
        )

    raise HTTPException(404, "Product not available")




# ---------------------------------------------------------------------------
# Product download (after purchase)
# ---------------------------------------------------------------------------

import io
import zipfile
from pathlib import Path as FilePath
from fastapi.responses import StreamingResponse


_STARTER_KIT_DIR = FilePath(__file__).resolve().parent.parent.parent / "starter-kit"


def _build_starter_kit_zip() -> bytes:
    """Build a zip archive of the starter-kit directory."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if _STARTER_KIT_DIR.is_dir():
            for fpath in sorted(_STARTER_KIT_DIR.rglob("*")):
                if fpath.is_file() and "__pycache__" not in str(fpath):
                    arcname = f"agentictrade-starter-kit/{fpath.relative_to(_STARTER_KIT_DIR)}"
                    zf.write(fpath, arcname)
    buf.seek(0)
    return buf.getvalue()


@router.get("/download/{product_id}")
async def product_download(
    product_id: str,
    request: Request = None,
):
    """
    Download product as zip (free — no payment verification required).

    Starter Kit is free to maximize developer adoption.
    Revenue comes from 10% platform commission on API calls.
    """
    if product_id not in PRODUCTS:
        raise HTTPException(404, f"Product not found: {product_id}")

    # Build and serve zip
    try:
        zip_data = _build_starter_kit_zip()
    except Exception as e:
        logger.error("Failed to build starter kit zip: %s", e)
        raise HTTPException(500, "Download preparation failed")

    if len(zip_data) < 100:
        raise HTTPException(500, "Starter kit files not found on server")

    return StreamingResponse(
        io.BytesIO(zip_data),
        media_type="application/zip",
        headers={
            "Content-Disposition": "attachment; filename=agentictrade-starter-kit.zip",
            "Content-Length": str(len(zip_data)),
        },
    )
