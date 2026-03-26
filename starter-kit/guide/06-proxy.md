# Chapter 6: The Proxy — SSRF Protection & Routing

## Why a Proxy?

In a marketplace, buyer agents call seller APIs. The naive approach is to give buyers the seller's URL directly. This has three problems:

1. **No billing** — you can't meter or charge for direct API calls
2. **No protection** — a malicious service could register an internal URL
3. **No monitoring** — you can't log quality, latency, or errors

The ACF proxy solves all three by sitting between buyer and seller:

```
Buyer Agent → ACF Proxy → Seller API
                │
         ┌──────┼──────┐
         │      │      │
       Auth   Bill   Log
```

## SSRF: The #1 Threat

Server-Side Request Forgery (SSRF) is the most dangerous vulnerability in any proxy system. An attacker registers a "service" pointing at internal infrastructure:

```json
{
  "name": "Cheap Data Service",
  "base_url": "http://169.254.169.254/latest/meta-data/",
  "price_per_call": 0.001
}
```

If the proxy blindly forwards requests, the attacker can:
- Read AWS/GCP/Azure instance metadata (including IAM credentials)
- Access internal databases, caches, admin panels
- Scan internal networks
- Exfiltrate data through the proxy

### ACF's SSRF Protection

The proxy implements defense-in-depth:

#### Layer 1: URL Validation at Registration

When a service is registered, the `base_url` is validated:

```python
def validate_base_url(url: str) -> bool:
    parsed = urlparse(url)

    # Must be http or https
    if parsed.scheme not in ("http", "https"):
        return False

    # Must have a hostname
    if not parsed.hostname:
        return False

    # Block obvious attacks
    if parsed.hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        return False

    return True
```

#### Layer 2: DNS Resolution Check

Before proxying, resolve the hostname and check the IP:

```python
import ipaddress
import socket

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),       # Private
    ipaddress.ip_network("172.16.0.0/12"),     # Private
    ipaddress.ip_network("192.168.0.0/16"),    # Private
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / cloud metadata
    ipaddress.ip_network("100.64.0.0/10"),     # CGNAT
    ipaddress.ip_network("::1/128"),           # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),          # IPv6 private
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
]

def is_safe_ip(hostname: str) -> bool:
    """Resolve hostname and check IP against blocked ranges."""
    try:
        ip_str = socket.gethostbyname(hostname)
        ip = ipaddress.ip_address(ip_str)
        return not any(ip in network for network in BLOCKED_NETWORKS)
    except socket.gaierror:
        return False  # Can't resolve = not safe
```

#### Layer 3: Redirect Following

Attackers can bypass DNS checks with redirects:

```
https://safe-looking.com → 302 → http://169.254.169.254
```

ACF prevents this by re-checking the IP after each redirect:

```python
async def safe_request(url, method, **kwargs):
    """Make HTTP request with SSRF protection on redirects."""
    # Don't follow redirects automatically
    response = await client.request(
        method, url, follow_redirects=False, **kwargs
    )

    if response.is_redirect:
        redirect_url = response.headers.get("location")
        parsed = urlparse(redirect_url)

        # Re-check the redirect target
        if not is_safe_ip(parsed.hostname):
            raise SSRFBlocked(f"Redirect to blocked IP: {redirect_url}")

        # Follow the safe redirect
        return await safe_request(redirect_url, method, **kwargs)

    return response
```

#### Layer 4: Configurable Allowlist

For environments with internal services that should be accessible:

```bash
# .env
ACF_INTERNAL_HOSTS=172.18.0.0/16,10.0.0.0/8
```

This allowlists specific internal ranges (e.g., Docker networks) while blocking everything else.

## Proxy Request Flow

The complete proxy flow:

```python
@router.post("/proxy/{service_id}/{path:path}")
async def proxy_request(
    service_id: str,
    path: str,
    request: Request,
    buyer_id: str = Query(...),
):
    # 1. Find service
    service = db.get_service(service_id)
    if not service or service.status != "active":
        raise HTTPException(404, "Service not found")

    # 2. Bill the call
    bill = bill_proxy_call(service, buyer_id)

    # 3. Build target URL
    target_url = f"{service.base_url.rstrip('/')}/{path}"

    # 4. SSRF check
    parsed = urlparse(target_url)
    if not is_safe_ip(parsed.hostname):
        raise HTTPException(403, "Blocked by SSRF protection")

    # 5. Forward request
    body = await request.body()
    headers = dict(request.headers)
    # Remove hop-by-hop headers
    for h in ("host", "content-length", "transfer-encoding"):
        headers.pop(h, None)

    start = time.monotonic()
    response = await safe_request(
        target_url,
        method=request.method,
        headers=headers,
        content=body,
        timeout=30,
    )
    latency_ms = (time.monotonic() - start) * 1000

    # 6. Log usage
    db.log_usage(
        service_id=service_id,
        buyer_id=buyer_id,
        amount=bill.amount,
        free_tier=bill.free_tier,
        status_code=response.status_code,
        response_time_ms=latency_ms,
    )

    # 7. Return with billing headers
    proxy_response = Response(
        content=response.content,
        status_code=response.status_code,
        media_type=response.headers.get("content-type"),
    )
    proxy_response.headers["X-ACF-Free-Tier"] = str(bill.free_tier).lower()
    proxy_response.headers["X-ACF-Amount"] = f"{bill.amount:.4f}"
    proxy_response.headers["X-ACF-Balance"] = f"{db.get_balance(buyer_id):.4f}"

    return proxy_response
```

## Timeout & Error Handling

The proxy handles seller API failures gracefully:

| Scenario | Buyer Charged? | Response |
|----------|---------------|----------|
| Seller returns 200 | Yes | Normal response |
| Seller returns 4xx | Yes (service was called) | Error forwarded |
| Seller returns 5xx | No (refunded) | 502 Bad Gateway |
| Seller timeout | No (refunded) | 504 Gateway Timeout |
| SSRF blocked | No | 403 Forbidden |
| Insufficient balance | No | 402 Payment Required |

## Exercise: Test SSRF Protection

1. Try registering a service with `base_url: http://169.254.169.254`
2. Try `base_url: http://127.0.0.1:8092` (self-referencing)
3. Register a service pointing to httpbin.org/redirect-to with a private IP target
4. Verify all three are blocked

```bash
# Test 1: Direct internal IP
curl -X POST https://agentictrade.io/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{"name":"SSRF Test","base_url":"http://169.254.169.254","price_per_call":0.01,"seller_id":"test"}'
# Should fail or be blocked when proxy call is made

# Test 2: Self-reference
curl -X POST https://agentictrade.io/api/v1/services \
  -H "Content-Type: application/json" \
  -d '{"name":"Self Ref","base_url":"http://127.0.0.1:8092","price_per_call":0.01,"seller_id":"test"}'
# Should be blocked
```

## Checkpoint

- [ ] Understand why a proxy is needed (billing, security, monitoring)
- [ ] Know the 4 layers of SSRF protection
- [ ] Understand the complete proxy request flow
- [ ] Know which failures refund the buyer vs charge

---

*Next: [Chapter 7 — Payment Integration →](./07-payments.md)*
