# TA Evaluation Round 12

**Date**: 2026-03-25
**Models**: Sonnet + Opus
**Result**: 6.0/10

## Personas

| Persona | Model | Score |
|---------|-------|-------|
| Hannah (Chief Risk Officer, Regulated Fintech) | Sonnet | 6.8 |
| Tomás (Principal Engineer, 40-person Platform Team) | Sonnet | 6.5 |
| Mei-Lin (VP Payments, Global Remittance) | Opus | 5.8 |
| Oleg (Staff SRE, 500M req/day API Gateway) | Opus | 4.9 |

## Summary

6 CRITICAL, 12 HIGH, 16 MEDIUM, 9 LOW

This round focused on **financial reconciliation** and **scalability under load** — two dimensions that prior rounds barely touched. The Opus SRE persona (Oleg) was particularly harsh, scoring 4.9/10 because the framework has fundamental architectural bottlenecks that would collapse at high traffic.

## CRITICAL Issues

### C1: Settlement create_settlement TOCTOU (duplicate check and insert in separate transactions)
- `settlement.py:109-145` — duplicate check in one `db.connect()`, insert in another
- Two concurrent requests can both pass the check and both insert
- **Money-doubling bug**
- Fix: Move check+insert into single transaction with BEGIN EXCLUSIVE

### C2: Settlement execute_payout read-check-update not atomic
- `settlement.py:239-322` — reads row in one connection, updates status in another
- Two concurrent execute_payout calls can both proceed to transfer_usdc
- Fix: Use UPDATE ... WHERE status IN ('pending','failed') with rowcount check

### C3: Escrow release_hold/refund_hold lack atomic guard
- `escrow.py:195-238` — read status then update, same TOCTOU pattern
- resolve_dispute was fixed (atomic UPDATE WHERE) but release/refund were not
- Fix: Same pattern as resolve_dispute

### C4: In-memory _rate_windows grows unboundedly (OOM)
- `auth.py:96,232-255` — dict keyed by API key, never evicted
- At 1M keys × 60 entries = ~480MB per worker
- Also not shared across workers (key gets N×limit with N workers)

### C5: psycopg2 (sync) blocks asyncio event loop
- `db.py:678,816-830` — ThreadedConnectionPool with blocking I/O on async FastAPI
- Every DB call serializes all coroutines on the event loop thread
- Fix: Use asyncpg or wrap in run_in_executor

### C6: SQLite per-request connection open/close (no pooling)
- `db.py:831-843` — new sqlite3.connect() + PRAGMAs on every call
- 3+ connections per request = massive FD churn

## HIGH Issues (12)

1. **Settlement not linked to usage_records** — no FK, overlapping periods double-count revenue
2. **PG BEGIN EXCLUSIVE→BEGIN translation removes serialization** — deduct_balance unsafe on PG
3. **Per-key rate limit in-memory, per-process** — N workers = N× effective limit
4. **Webhook delivery blocks event loop** — 3 retries × asyncio.sleep = 7s per delivery
5. **batch_create_keys sequential** — 50 keys = 50 DB round-trips + 50 scrypt hashes
6. **_PGConnWrapper single cursor** — shared cursor state can be overwritten by sequential queries
7. **No credit_balance upper bound** — unlimited batch deposits possible
8. **Proxy deduct-then-forward partial failure** — crash after deduction = permanent balance loss
9. **Escrow auto-resolve two-step non-atomic** — disputed→held→released, crash leaves inconsistent
10. **confirm_deposit doesn't credit balance** — marked confirmed but buyer never receives funds
11. **New httpx.AsyncClient per webhook delivery** — no connection reuse, TLS handshake per attempt
12. **No graceful shutdown** — lifespan has no teardown, in-flight requests killed mid-settlement

## MEDIUM Issues (16)

1. get_usage_stats unbounded full table scan
2. No index on usage_records.provider_id
3. list_webhooks_for_event full table scan + decrypt all
4. list_escrow_holds no LIMIT
5. credit_balance inflates total_deposited on refunds
6. No lifespan shutdown hook (PG pool never closed)
7. batch_deposits no idempotency
8. list_settlements no index on period_end
9. batch_usage unbounded IN clause
10. No readiness vs liveness health probe separation
11. PG_POOL_MAX=20 too low for async workloads
12. process_releasable not idempotent under concurrent execution
13. No multi-currency/FX support
14. settlement.py:140 still uses float() in INSERT (regression from earlier fix?)
15. Webhook dispatch fire-and-forget no backpressure
16. get_commission_rate 3+ DB connections per call

## LOW Issues (9)

1. JSON logger missing request_id
2. _PGConnWrapper._begin() no-op for DDL
3. PG pool no metrics/monitoring
4. executescript splits on ; naively
5. CORS allows all methods/headers
6. founding_sellers.commission_rate still REAL
7. Webhook _deliver dead code
8. No audit trail for balance mutations
9. Settlement status no CHECK constraint

---

## Progress Summary (R7→R12)

| Round | Score | CRIT | HIGH | MED | LOW | Tests | Focus |
|-------|-------|------|------|-----|-----|-------|-------|
| R7 | 7.4 | 0 | 0 | P0+P1 | - | 1341 | General |
| R8 | 8.45 | 0 | 0 | 5 | 0 | 1407 | DX + API completeness |
| R9 | 7.25 | 0 | 2 | 12 | 0 | 1431 | Security + PG compat |
| R10 | 7.1 | 0 | 0 | 3 | 5 | 1431 | Pentesting + CTO |
| R11 | 7.3 | 4 | 9 | 14 | 9 | 1431 | Financial + code quality |
| R12 | 6.0 | 6 | 12 | 16 | 9 | 1431 | Reconciliation + scale |

Note: R12 scores are lower because personas specifically targeted financial reconciliation (CRO) and high-traffic scalability (SRE) — areas where the framework has architectural gaps rather than fixable bugs. Many R12 issues require architectural changes (async DB, connection pooling, event queues) rather than point fixes.
