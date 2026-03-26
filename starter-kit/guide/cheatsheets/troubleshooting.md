# Troubleshooting Guide

## Common Issues

### Server Won't Start

**Symptom**: `docker compose up` fails

```bash
# Check if port 8092 is in use
lsof -i :8092

# Check Docker is running
docker info

# Check logs
docker compose logs app
```

**Fix**: Kill the process using port 8092, or change the port in docker-compose.yml.

---

### 402 Payment Required

**Symptom**: Proxy calls return 402

```bash
# Check buyer balance
curl https://agentictrade.io/api/v1/balance/YOUR_BUYER_ID
```

**Fix**: Add credits:
```bash
curl -X POST "https://agentictrade.io/api/v1/admin/credit?buyer_id=YOUR_BUYER_ID&amount=10&admin_key=test-admin-secret"
```

---

### SSRF Blocked (403)

**Symptom**: Service calls return 403 "Blocked by SSRF protection"

**Cause**: Service `base_url` points to a private/internal IP.

**Fix**: Use a publicly accessible URL. If you need to reach an internal service, configure `ACF_INTERNAL_HOSTS` in `.env`:
```bash
ACF_INTERNAL_HOSTS=172.18.0.0/16
```

---

### Deposit Not Credited

**Symptom**: Crypto payment sent but balance not updated

1. Check deposit status:
```bash
curl https://agentictrade.io/api/v1/deposits?buyer_id=YOUR_ID
```

2. Check IPN logs:
```bash
docker compose logs app | grep IPN
```

3. Common causes:
   - IPN callback URL not reachable from NOWPayments
   - `NOWPAYMENTS_IPN_SECRET` mismatch
   - Payment still pending confirmations

**Fix**: Verify IPN secret matches, ensure callback URL is publicly accessible.

---

### Slow Proxy Responses

**Symptom**: Service calls take > 5 seconds

1. Check seller API directly:
```bash
curl -w "\nTime: %{time_total}s\n" https://seller-api.com/endpoint
```

2. Check ACF proxy overhead:
```bash
# Compare direct vs proxied
time curl https://agentictrade.io/api/v1/proxy/SERVICE_ID/endpoint?buyer_id=test
```

**Fix**: If seller API is slow, increase proxy timeout:
```nginx
# In nginx/acf.conf
proxy_read_timeout 120s;
```

---

### Database Locked

**Symptom**: `sqlite3.OperationalError: database is locked`

**Cause**: Multiple processes writing to SQLite simultaneously.

**Fix**: Ensure only one app instance is running:
```bash
docker compose ps
# Should show only 1 "app" container
```

For high concurrency, configure WAL mode:
```python
# In db initialization
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA busy_timeout=5000")
```

---

### SSL Certificate Issues

**Symptom**: HTTPS not working or certificate warnings

```bash
# Check certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Renew if expired
sudo certbot renew
docker compose restart nginx
```

---

### Rate Limiting Too Aggressive

**Symptom**: 429 Too Many Requests

**Fix**: Adjust Nginx rate limits:
```nginx
# More generous limits
limit_req_zone $binary_remote_addr zone=api:20m rate=100r/s;
limit_req zone=api burst=100 nodelay;
```

---

### Webhook Not Received

**Symptom**: Webhook consumer not getting events

1. Check consumer is running:
```bash
curl http://localhost:9100/health
```

2. Check ACF can reach consumer:
```bash
# From ACF container
docker compose exec app curl http://host.docker.internal:9100/webhook
```

3. Verify registration:
```bash
curl https://agentictrade.io/api/v1/webhooks
```

**Fix**: Ensure webhook URL is reachable from ACF. Use Docker network names if both are in Docker.

## Debug Commands

```bash
# Check all services
curl -s https://agentictrade.io/api/v1/services | python3 -m json.tool

# Check specific service
curl -s https://agentictrade.io/api/v1/services/SERVICE_ID | python3 -m json.tool

# Check all balances (admin)
sqlite3 /path/to/marketplace.db "SELECT * FROM balances;"

# Check usage records
sqlite3 /path/to/marketplace.db "SELECT * FROM usage_records ORDER BY created_at DESC LIMIT 20;"

# Check deposits
sqlite3 /path/to/marketplace.db "SELECT * FROM deposits ORDER BY created_at DESC LIMIT 10;"

# Full smoke test
python cli/acf_test_payment.py --url https://agentictrade.io
```

## Getting Help

- **API Docs**: https://agentictrade.io/docs
- **GitHub Issues**: https://github.com/judyailab/agent-commerce-framework/issues
- **Framework Source**: https://github.com/judyailab/agent-commerce-framework
