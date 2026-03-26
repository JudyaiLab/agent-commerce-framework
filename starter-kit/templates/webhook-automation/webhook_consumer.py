#!/usr/bin/env python3
"""
AgenticTrade Webhook Consumer.

Production-grade event consumer with:
- HMAC-SHA256 signature verification
- Replay protection (timestamp check)
- Exponential backoff retry
- Dead-letter queue for failed events
- Optional Slack/Telegram notifications

Usage:
    python webhook_consumer.py                    # Start consumer
    python webhook_consumer.py --replay dead_letter/  # Replay failed events
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

# ─── Config ─────────────────────────────────────────────

CONFIG_PATH = Path(__file__).parent / "config.yaml"

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config not found: {CONFIG_PATH}\n"
            "Copy config.example.yaml to config.yaml and fill in your values."
        )
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


# ─── Logging ────────────────────────────────────────────

def setup_logging(cfg: dict) -> logging.Logger:
    log_cfg = cfg.get("logging", {})
    level = getattr(logging, log_cfg.get("level", "INFO").upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_file = log_cfg.get("file", "")
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(level=level, handlers=handlers,
                        format="%(asctime)s %(levelname)s %(message)s")
    return logging.getLogger("webhook")


# ─── Signature Verification ─────────────────────────────

def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from ACF server."""
    expected = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def check_replay(timestamp_str: str, max_age_sec: int = 300) -> bool:
    """Reject events older than max_age_sec (default 5 minutes)."""
    try:
        ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return abs(age) <= max_age_sec
    except (ValueError, TypeError):
        return False


# ─── Notifications ──────────────────────────────────────

def notify_slack(webhook_url: str, text: str) -> None:
    try:
        httpx.post(webhook_url, json={"text": text}, timeout=10)
    except Exception:
        pass  # Best-effort notification


def notify_telegram(bot_token: str, chat_id: str, text: str) -> None:
    try:
        httpx.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def send_notification(cfg: dict, message: str) -> None:
    notif = cfg.get("notifications", {})
    slack = notif.get("slack", {})
    if slack.get("enabled") and slack.get("webhook_url"):
        notify_slack(slack["webhook_url"], message)
    tg = notif.get("telegram", {})
    if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
        notify_telegram(tg["bot_token"], tg["chat_id"], message)


# ─── Event Handlers ─────────────────────────────────────

def handle_payment_confirmed(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    buyer = data.get("buyer_id", "unknown")
    amount = data.get("amount", 0)
    log.info(f"Payment confirmed: {buyer} deposited ${amount}")
    # TODO: Activate credits, update your database, trigger workflows


def handle_payment_failed(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    buyer = data.get("buyer_id", "unknown")
    reason = data.get("reason", "unknown")
    log.warning(f"Payment failed: {buyer} — {reason}")


def handle_service_registered(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    name = data.get("name", "unknown")
    service_id = data.get("service_id", "unknown")
    log.info(f"New service registered: {name} ({service_id})")
    # TODO: Run quality check, update search index


def handle_service_updated(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    service_id = data.get("service_id", "unknown")
    log.info(f"Service updated: {service_id}")


def handle_proxy_called(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    service_id = data.get("service_id", "unknown")
    buyer = data.get("buyer_id", "unknown")
    amount = data.get("amount", 0)
    log.info(f"Proxy call: {buyer} → {service_id} (${amount})")
    # TODO: Update analytics, check budget alerts


def handle_settlement_completed(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    seller = data.get("seller_id", "unknown")
    amount = data.get("amount", 0)
    log.info(f"Settlement: ${amount} paid to {seller}")
    # TODO: Accounting reconciliation


def handle_balance_low(event: dict, cfg: dict, log: logging.Logger) -> None:
    data = event.get("data", {})
    buyer = data.get("buyer_id", "unknown")
    balance = data.get("balance", 0)
    threshold = cfg.get("handlers", {}).get("balance.low", {}).get("threshold", 1.0)
    log.warning(f"Low balance: {buyer} has ${balance} (threshold: ${threshold})")
    # TODO: Auto top-up or send alert


HANDLER_MAP = {
    "payment.confirmed": handle_payment_confirmed,
    "payment.failed": handle_payment_failed,
    "service.registered": handle_service_registered,
    "service.updated": handle_service_updated,
    "proxy.called": handle_proxy_called,
    "settlement.completed": handle_settlement_completed,
    "balance.low": handle_balance_low,
}


# ─── Dead-Letter Queue ──────────────────────────────────

def write_dead_letter(event: dict, error: str, cfg: dict) -> Path:
    dlq_dir = Path(cfg.get("retry", {}).get("dead_letter_dir", "dead_letter"))
    dlq_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    event_type = event.get("event", "unknown")
    event_id = event.get("id", "noid")[:8]
    filename = f"{ts}_{event_type}_{event_id}.json"
    path = dlq_dir / filename
    dlq_data = {"event": event, "error": error, "failed_at": ts}
    path.write_text(json.dumps(dlq_data, indent=2, default=str))
    return path


# ─── Retry Logic ────────────────────────────────────────

def process_with_retry(event: dict, cfg: dict, log: logging.Logger) -> bool:
    """Process event with exponential backoff retry."""
    event_type = event.get("event", "unknown")
    handler_cfg = cfg.get("handlers", {}).get(event_type, {})

    if not handler_cfg.get("enabled", True):
        log.debug(f"Handler disabled for {event_type}, skipping")
        return True

    handler = HANDLER_MAP.get(event_type)
    if not handler:
        log.warning(f"No handler for event type: {event_type}")
        return True  # Don't retry unknown events

    retry_cfg = cfg.get("retry", {})
    max_attempts = retry_cfg.get("max_attempts", 5)
    delay = retry_cfg.get("initial_delay_sec", 2)
    multiplier = retry_cfg.get("backoff_multiplier", 2.0)
    max_delay = retry_cfg.get("max_delay_sec", 60)

    for attempt in range(1, max_attempts + 1):
        try:
            handler(event, cfg, log)

            # Send notification if configured
            if handler_cfg.get("notify"):
                data = event.get("data", {})
                msg = f"[ACF] {event_type}: {json.dumps(data, default=str)[:200]}"
                send_notification(cfg, msg)

            return True
        except Exception as e:
            log.error(f"Handler failed (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                log.info(f"Retrying in {delay}s...")
                time.sleep(delay)
                delay = min(delay * multiplier, max_delay)

    # All retries exhausted → dead-letter queue
    path = write_dead_letter(event, "max retries exceeded", cfg)
    log.error(f"Event sent to dead-letter queue: {path}")
    send_notification(cfg, f"[ACF DLQ] Event {event_type} failed after {max_attempts} attempts")
    return False


# ─── FastAPI App ────────────────────────────────────────

app = FastAPI(title="ACF Webhook Consumer")
_cfg: dict = {}
_log: logging.Logger = logging.getLogger("webhook")


@app.on_event("startup")
def startup():
    global _cfg, _log
    _cfg = load_config()
    _log = setup_logging(_cfg)
    _log.info("Webhook consumer started")


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_acf_signature: str = Header(default="", alias="X-ACF-Signature"),
    x_acf_timestamp: str = Header(default="", alias="X-ACF-Timestamp"),
):
    body = await request.body()

    # Verify signature
    secret = _cfg.get("webhook_secret", "")
    if secret and not verify_signature(body, x_acf_signature, secret):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Replay protection
    if x_acf_timestamp and not check_replay(x_acf_timestamp):
        raise HTTPException(status_code=400, detail="Event too old (replay rejected)")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("event", "unknown")
    event_id = event.get("id", "unknown")
    _log.info(f"Received event: {event_type} ({event_id})")

    # Process asynchronously (in production, use a task queue)
    ok = process_with_retry(event, _cfg, _log)

    return JSONResponse(
        status_code=200 if ok else 202,
        content={"received": True, "processed": ok},
    )


@app.get("/health")
def health():
    return {"status": "ok", "service": "webhook-consumer"}


# ─── Dead-Letter Replay ────────────────────────────────

def replay_dead_letters(dlq_dir: str, cfg: dict, log: logging.Logger) -> None:
    dlq_path = Path(dlq_dir)
    if not dlq_path.exists():
        print(f"Directory not found: {dlq_dir}")
        return

    files = sorted(dlq_path.glob("*.json"))
    if not files:
        print("No dead-letter files found.")
        return

    print(f"Found {len(files)} dead-letter events. Replaying...")
    success = 0
    for f in files:
        try:
            dlq_data = json.loads(f.read_text())
            event = dlq_data["event"]
            ok = process_with_retry(event, cfg, log)
            if ok:
                f.unlink()  # Remove successfully replayed event
                success += 1
                print(f"  OK: {f.name}")
            else:
                print(f"  FAIL: {f.name}")
        except Exception as e:
            print(f"  ERROR: {f.name} — {e}")

    print(f"\nReplayed: {success}/{len(files)} succeeded")


# ─── CLI ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="ACF Webhook Consumer")
    parser.add_argument("--replay", metavar="DIR",
                        help="Replay dead-letter events from directory")
    parser.add_argument("--host", default=None, help="Override listen host")
    parser.add_argument("--port", type=int, default=None, help="Override listen port")
    args = parser.parse_args()

    cfg = load_config()
    log = setup_logging(cfg)

    if args.replay:
        replay_dead_letters(args.replay, cfg, log)
        return

    import uvicorn
    host = args.host or cfg.get("server", {}).get("host", "127.0.0.1")
    port = args.port or cfg.get("server", {}).get("port", 9100)
    log.info(f"Starting webhook consumer on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
