# Chapter 10: Production Deployment

This chapter covers deploying **your own API service** behind the AgenticTrade marketplace. You don't need to run the marketplace itself — that's hosted at [agentictrade.io](https://agentictrade.io).

## Deployment Architecture

```
Internet
   │
   ▼
┌─────────────────────────────┐
│  AgenticTrade Marketplace   │  ← Hosted for you
│  (agentictrade.io)          │
└──────────┬──────────────────┘
           │ proxied requests
           ▼
┌──────────────────────────┐
│  Nginx (SSL termination) │  ← Your server
│  - Rate limiting          │
│  - Security headers       │
└──────────┬───────────────┘
           │
    ┌──────▼──────┐
    │  Your API   │
    │  Service    │
    └─────────────┘
```

## Step 1: Environment Variables

```bash
cp deploy/.env.production.template .env
```

Edit `.env` with your values:

```bash
# Your marketplace connection
ACF_MARKETPLACE_URL=https://agentictrade.io
ACF_API_KEY=your_key_id:your_secret

# Your API service
PORT=8080

# Payment: wallet address for receiving USDC payouts
WALLET_ADDRESS=0x...

# Your domain for SSL
DOMAIN=yourdomain.com
```

> **Security**: Never commit `.env` to git. The `.gitignore` already excludes it.

## Step 2: SSL Certificates

Use Let's Encrypt for free SSL:

```bash
# Install certbot
sudo apt install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificates saved to:
# /etc/letsencrypt/live/yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/yourdomain.com/privkey.pem
```

## Step 3: Configure Nginx

Edit `deploy/nginx/acf.conf`:

```nginx
# Replace all instances of "yourdomain.com" with your actual domain
server_name yourdomain.com;
ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
```

### Rate Limiting

The default config has three rate limit zones:

| Zone | Rate | Applies To |
|------|------|-----------|
| `api` | 30 req/s | General API endpoints |
| `proxy` | 10 req/s | Service proxy calls (cost money) |
| (none) | Unlimited | Health check, IPN callbacks |

Adjust based on your expected traffic:

```nginx
# High-traffic marketplace
limit_req_zone $binary_remote_addr zone=api:20m rate=100r/s;
limit_req_zone $binary_remote_addr zone=proxy:20m rate=50r/s;
```

### Security Headers

The config includes production-grade security headers:

```nginx
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

## Step 4: Launch

```bash
cd deploy/
docker compose -f docker-compose.prod.yml up -d
```

Verify:

```bash
# Health check — your API
curl https://yourdomain.com/health

# Verify marketplace connection
python cli/acf_test_payment.py --api-key $ACF_API_KEY
```

## Step 5: Monitoring

### Health Check Endpoint

Your app should include a health check endpoint:

```bash
# Docker will restart the app if health check fails
curl http://localhost:8080/health
```

Docker Compose is configured to check every 30 seconds:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

### Log Monitoring

```bash
# App logs
docker compose -f docker-compose.prod.yml logs -f app

# Nginx access logs
docker compose -f docker-compose.prod.yml logs -f nginx

# All logs
docker compose -f docker-compose.prod.yml logs -f
```

### Key Metrics to Watch

| Metric | Source | Alert Threshold |
|--------|--------|----------------|
| Response time | Nginx logs | > 5s |
| Error rate (5xx) | Nginx logs | > 1% |
| Disk usage | `df -h` | > 80% |
| SQLite DB size | `ls -lh /data/` | > 1GB |
| Memory usage | `docker stats` | > 450MB |

### External Monitoring

Set up an external uptime check:

```bash
# Example with curl in crontab
*/5 * * * * curl -sf https://yourdomain.com/health || echo "ACF DOWN" | mail admin@yourdomain.com
```

## Step 6: Backups

SQLite databases need regular backups:

```bash
# Backup script (add to crontab)
#!/bin/bash
BACKUP_DIR=/backups/acf
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
docker compose -f docker-compose.prod.yml exec app \
  sqlite3 /data/marketplace.db ".backup /data/backup_${DATE}.db"
docker compose -f docker-compose.prod.yml cp app:/data/backup_${DATE}.db $BACKUP_DIR/
# Keep last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
```

## Step 7: SSL Auto-Renewal

```bash
# Add to crontab
0 2 * * * certbot renew --quiet && docker compose -f deploy/docker-compose.prod.yml restart nginx
```

## Resource Limits

The Docker Compose config includes resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: "1.0"
```

For higher traffic, increase:

```yaml
# High-traffic config
deploy:
  resources:
    limits:
      memory: 2G
      cpus: "4.0"
```

## Scaling Beyond Single Server

When you outgrow a single server:

1. **Database**: Migrate from SQLite to PostgreSQL
2. **Cache**: Redis is already included for rate limiting
3. **Load balancing**: Run multiple app instances behind Nginx
4. **CDN**: Put Cloudflare in front for DDoS protection

```
Users → Cloudflare → Nginx → App 1, App 2, App 3 → PostgreSQL
```

## Security Checklist

Before going live:

- [ ] `ACF_ADMIN_SECRET` is a strong random value (not `test-admin-secret`)
- [ ] SSL certificates are valid and auto-renewing
- [ ] CORS origins restrict to your domain only
- [ ] No services registered with internal base URLs
- [ ] Rate limiting is configured
- [ ] Database backups are scheduled
- [ ] Monitoring alerts are set up
- [ ] `.env` is not in git

## Exercise: Deploy to a VPS

1. Spin up a VPS ($5/month — DigitalOcean, Hetzner, etc.)
2. Point your domain to the server
3. Follow Steps 1-7 above
4. Run the smoke test from your local machine
5. Register a real service and make a purchase

## Checkpoint

- [ ] Production `.env` configured with real secrets
- [ ] SSL certificates installed and auto-renewing
- [ ] Nginx reverse proxy with rate limiting
- [ ] Docker Compose running app + nginx + redis
- [ ] Health check passing
- [ ] Backups scheduled
- [ ] Monitoring configured

---

*Next: [Chapter 11 — Monetization Strategies →](./11-monetization.md)*
