# TA Evaluation Round 11

**Date**: 2026-03-25
**Models**: Sonnet + Opus
**Result**: 7.3/10

## Personas

| Persona | Model | Score |
|---------|-------|-------|
| Lena (VP Engineering, Series B) | Sonnet | 7.4 |
| Raj (Solo AI Developer) | Sonnet | 6.8 |
| Sofia (Head of Platform Security, Crypto Exchange) | Opus | 7.3 |
| Derek (CTO, Mid-Size SaaS) | Opus | 7.8 |

## Summary

4 CRITICAL, 9 HIGH, 14 MEDIUM, 9 LOW

### CRITICAL Issues Found & Fixed
1. **Float precision loss** — All monetary DB columns used REAL (float64), Decimal→float() conversion on writes. Fixed: REAL→TEXT schema, float()→str() at write boundaries, Decimal on reads.
2. **Bootstrap TOCTOU** — Check and create in separate transactions. Fixed: Single BEGIN EXCLUSIVE transaction with check+INSERT.
3. **Webhook secret plaintext** — Secrets stored unencrypted in DB. Fixed: XOR encryption with HMAC-SHA256 counter-mode keystream + per-secret nonce.
4. **Settlement retry double-pay** — Failed retries generated new idempotency keys. Fixed: Reuse existing key on failed→retry.

### HIGH Issues Found & Fixed
1. **Provider wallet verification skip** — No agent record = no check. Fixed: Mandatory verification, missing record raises error.
2. **auth_success audit missing** — Only failures logged. Fixed: Added auth_success event after successful validation.
3. **Escrow resolve_dispute race** — Two admins could resolve same dispute. Fixed: Atomic UPDATE WHERE status='disputed' + rowcount check.
4. **Webhook secret min length** — 1-char secret allowed. Fixed: Minimum 16 characters enforced.
5. **Settlement retry idempotency gap** — New key on retry. Fixed: Reuse existing key.

### MEDIUM Issues (14) — Pending
- In-memory rate limiter no eviction (memory leak)
- No batch deposit idempotency
- Batch auth bypass (no brute-force counter)
- Commission micropayment rate not used in settlement
- Escrow dispute submitted_by not authenticated
- Webhook _deliver dead code
- DatabaseRateLimiter unbounded counter growth
- Rate limit header reports IP limit not key limit
- list_settlements no auth scope
- Proxy no body size limit
- get_provider_escrow_summary loads all into memory
- get_commission_rate 3+ DB round-trips per call
- get_effective_rate instantiates HealthMonitor per call
- Webhook retry window too short (7s total)

### LOW Issues (9)
- ETH address 0x prefix validation semantics
- transfer_usdc silent None on zero amount
- No component health check (readiness vs liveness)
- CSP nonce on API responses (unnecessary)
- No lifespan shutdown hook
- CORS allows all methods/headers
- Inline import in loop (commission.py)
- Two migration tracking tables
- JSON logger missing request ID

**Tests after fix**: 1431 passed, 0 failed

---

## Progress Summary (R7→R11)

| Round | Score | CRIT | HIGH | MED | LOW | Tests |
|-------|-------|------|------|-----|-----|-------|
| R7 | 7.4 | 0 | 0 | P0+P1 | - | 1341 |
| R8 | 8.45 | 0 | 0 | 5 | 0 | 1407 |
| R9 | 7.25 | 0 | 2 | 12 | 0 | 1431 |
| R10 | 7.1 | 0 | 0 | 3 | 5 | 1431 |
| R11 | 7.3 | 4 | 9 | 14 | 9 | 1431 |

Note: Scores don't always increase because each round uses different personas with different expertise depths. Opus evaluators tend to find deeper systemic issues (e.g. R11 found the float precision problem that prior rounds missed).
