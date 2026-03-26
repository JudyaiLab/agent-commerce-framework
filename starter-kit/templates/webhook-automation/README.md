# Webhook Automation Template

> Production-grade event consumer for AgenticTrade marketplace events.

Handles payment confirmations, service registrations, usage alerts, and settlement notifications with automatic retries, dead-letter queue, and optional Slack/Telegram notifications.

## Events

| Event | Trigger | Typical Use |
|-------|---------|-------------|
| `payment.confirmed` | Deposit confirmed on-chain | Activate buyer credits |
| `payment.failed` | Deposit expired or rejected | Alert ops team |
| `service.registered` | New service listed | Quality check, index update |
| `service.updated` | Service config changed | Re-validate pricing |
| `proxy.called` | API proxy invocation | Usage analytics |
| `settlement.completed` | Seller payout sent | Accounting reconciliation |
| `balance.low` | Buyer balance below threshold | Auto top-up or alert |

## Architecture

```
ACF Server ──POST──▶ webhook_consumer.py
                         │
                    ┌─────┴─────┐
                    │  Router   │
                    └─────┬─────┘
              ┌───────┬───┴───┬──────┐
              ▼       ▼       ▼      ▼
          handler  handler  handler  DLQ
          (pay)   (svc)    (proxy)  (retry)
              │       │       │
              ▼       ▼       ▼
          Slack   Database  Analytics
```

## Quick Start

```bash
# 1. Configure
cp config.example.yaml config.yaml
# Edit: set your ACF server URL, webhook secret, notification channels

# 2. Run consumer
python webhook_consumer.py

# 3. Register webhook with ACF
curl -X POST https://agentictrade.io/api/v1/webhooks/register \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://your-host:9100/webhook",
    "events": ["payment.confirmed", "settlement.completed"],
    "secret": "your-webhook-secret"
  }'
```

## Configuration

See `config.example.yaml` for all options. Key settings:

- **webhook_secret**: HMAC secret shared with ACF server (must match registration)
- **retry**: Exponential backoff with configurable max attempts and dead-letter queue
- **notifications**: Slack webhook URL and/or Telegram bot token for alerts
- **handlers**: Enable/disable individual event handlers

## Dead-Letter Queue

Failed events (after max retries) are written to `dead_letter/` as JSON files:

```
dead_letter/
  2026-03-20T08-15-30_payment.confirmed_abc123.json
```

Replay them manually:
```bash
python webhook_consumer.py --replay dead_letter/
```

## Security

- All incoming webhooks are verified via HMAC-SHA256 signature
- Replay protection via timestamp check (rejects events older than 5 minutes)
- Consumer binds to 127.0.0.1 by default (use reverse proxy for external access)
