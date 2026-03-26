# AgenticTrade API Quick Reference

## Services

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/services` | List/search services |
| `GET` | `/api/v1/services/{id}` | Get service details |
| `POST` | `/api/v1/services` | Register new service |
| `PATCH` | `/api/v1/services/{id}` | Update service |
| `DELETE` | `/api/v1/services/{id}` | Remove service |

### Search Parameters

```
GET /api/v1/services?q=crypto&category=data&max_price=0.10&status=active
```

| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Text search (name + description) |
| `category` | string | Filter by category |
| `max_price` | float | Maximum price per call |
| `min_free_tier` | int | Minimum free tier calls |
| `status` | string | active, paused, archived |

## Billing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/balance/{buyer_id}` | Check balance |
| `POST` | `/api/v1/deposits` | Create deposit (crypto) |
| `POST` | `/api/v1/deposits/stripe` | Create deposit (fiat) |
| `POST` | `/api/v1/admin/credit` | Test credit (admin only) |

## Proxy

| Method | Endpoint | Description |
|--------|----------|-------------|
| `ANY` | `/api/v1/proxy/{service_id}/{path}` | Call service |

### Query Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `buyer_id` | Yes | Buyer agent ID |

### Response Headers

| Header | Description |
|--------|-------------|
| `X-ACF-Free-Tier` | "true" or "false" |
| `X-ACF-Amount` | Amount charged (USD) |
| `X-ACF-Balance` | Remaining balance |
| `X-ACF-Service` | Service ID |

### Error Codes

| Code | Meaning |
|------|---------|
| 200 | Success (charged) |
| 402 | Insufficient balance |
| 403 | SSRF blocked |
| 404 | Service not found |
| 502 | Seller API error (refunded) |
| 504 | Seller API timeout (refunded) |

## Settlement

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/settlement/status/{seller_id}` | Seller balance |
| `POST` | `/api/v1/settlement/run` | Trigger payout |

## Identity

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/identity/register` | Register agent identity |
| `GET` | `/api/v1/identity/{agent_id}` | Get agent info |

## Reputation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/reputation/{agent_id}` | Get reputation score |

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/keys` | Create API key |
| `DELETE` | `/api/v1/auth/keys/{key_id}` | Revoke API key |

### Using API Keys

```
Authorization: Bearer {key_id}:{secret}
```

## Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/openapi.json` | OpenAPI spec |

## Webhooks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/webhooks/register` | Register webhook |
| `DELETE` | `/api/v1/webhooks/{id}` | Remove webhook |

### Webhook Events

```
payment.confirmed | payment.failed | service.registered
service.updated | proxy.called | settlement.completed | balance.low
```

## IPN Callbacks

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/ipn/nowpayments` | NOWPayments callback |
| `POST` | `/api/v1/ipn/stripe` | Stripe webhook |
