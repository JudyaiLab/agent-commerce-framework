# API Monetization Template

Turn any existing REST API into a paid service on the AgenticTrade marketplace in under 30 minutes.

## What This Does

1. Wraps your existing API behind the ACF payment proxy
2. Sets up metered billing (per-call pricing + free tier)
3. Handles crypto deposits via NOWPayments
4. Provides a revenue tracking dashboard

## Quick Start

```bash
# 1. Configure your API
cp config.example.yaml config.yaml
# Edit config.yaml with your API details and pricing

# 2. Register on the marketplace
python register_services.py

# 3. Test the payment flow
python test_flow.py

# 4. Share your service endpoint with buyers
# They call: POST /api/v1/proxy/{service_id}/your-endpoint
```

## Files

| File | Description |
|------|-------------|
| `config.example.yaml` | Service configuration template |
| `register_services.py` | Bulk-register services from YAML config |
| `wrap_api.py` | Adapter to proxy requests to your existing API |
| `test_flow.py` | End-to-end payment flow smoke test |
| `revenue_dashboard.html` | Standalone revenue tracking page |

## Revenue Model

- Set your price per call (e.g., $0.50)
- Platform takes 10% fee
- You receive 90% via settlement
- Free tier attracts trial users, converts to paid
