# TA Evaluation Report — Round 28

| Field | Value |
|-------|-------|
| **Result**: **8.9/10** | |
| **Round** | 28 |
| **Date** | 2026-03-25 |
| **Rotation** | Finance (R28 mod 4 = 0) |
| **Evaluator** | J (COO / Technical Director) |
| **Overall Score** | **8.9 / 10** |
| **Pass Streak** | 0 / 5 (need 5 consecutive ≥ 9.0) |
| **Verdict** | FAIL — below 9.0 threshold |

---

## Executive Summary

Round 28 applies a **Finance rotation** lens — evaluating the framework through the eyes of a Chief Revenue Officer, Forensic Accountant, Treasury AI Agent, and Revenue Reconciliation Bot. This round achieves **8.9/10** (same as R27), driven by **2 fixes verified** from R27:

- **R27-M1** (idempotency response uses wrong ProxyResult constructor) is **FIXED** — `forward_request()` idempotency path now correctly creates `ProxyResult` with `billing=BillingInfo(...)` and `error=None`, matching the constructor signature.
- **R27-L2** (trending endpoint uses all-time data) is **FIXED** — `get_trending()` now accepts a `days` parameter (default 7) and filters with `AND timestamp >= ?` using a computed cutoff.

One new MEDIUM found: `mark_paid()` uses `WHERE status = 'pending'` but `execute_payout()` transitions the settlement to `'processing'` before calling it — meaning successful automated payouts never get their status updated to `'completed'` in the database, creating a reconciliation discrepancy and potential double-payout risk via the recovery pipeline.

Active issues reduced from 1M + 5L to **1M + 4L** — the framework needs one settlement status fix to reach 9.0.

---

## Methodology

- **Code review**: All `marketplace/*.py` (29 files), `api/main.py`, `api/routes/*.py` (27 routes), `payments/*.py` (7 files) read and analyzed
- **Verification**: Each R27 finding independently verified via code inspection (GATE-6 anti-fabrication)
- **Constructor verification**: `ProxyResult.__init__` at proxy.py:452-468 cross-referenced with idempotency path at proxy.py:172-185 — `BillingInfo(...)` and `error=None` now match `__slots__`
- **Trending query verification**: `get_trending()` at discovery.py:146-164 — `since` computed from `days` parameter, used in `WHERE ... AND timestamp >= ?`
- **Settlement state machine audit**: `execute_payout()` (settlement.py:324-425) traced through status transitions: pending → processing → (mark_paid attempts pending→completed, fails) → stuck in processing
- **Persona rotation**: Finance focus — 2 human decision-makers + 2 AI agent personas, each scoring independently

---

## R27 Issue Verification (GATE-6: Independent Re-Run)

| R27 ID | Issue | Status | Evidence |
|--------|-------|--------|----------|
| R27-M1 | Idempotency response path uses wrong ProxyResult constructor args | **FIXED** | `proxy.py:172-185`: idempotency path now constructs `ProxyResult(status_code=..., body=..., headers=..., latency_ms=..., billing=BillingInfo(amount=cached_amount, platform_fee=Decimal("0"), provider_amount=cached_amount, usage_id=existing.get("id",""), free_tier=cached_amount==0), error=None)`. Matches `ProxyResult.__init__` signature at line 452 and `__slots__` at line 450. |
| R27-L2 | Trending endpoint uses all-time data without time window | **FIXED** | `discovery.py:146-164`: `get_trending(self, limit=10, days=7)` now computes `since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()` and passes it as parameter to `WHERE status_code < 500 AND timestamp >= ?`. Default 7-day window. |

---

## Already Fixed Issues (Not Re-Reported)

The following 84+ issues from R1–R27 have been verified as fixed and are excluded from scoring. Notable additions verified this round:

1. R27-M1: Idempotency ProxyResult constructor → FIXED (proxy.py:172-185 uses BillingInfo + error=None)
2. R27-L2: Trending time window filter → FIXED (discovery.py:146-164 uses `days` parameter with `AND timestamp >= ?`)

See R27 report for the complete prior-round fix list (82+ items from R1–R26, plus R17-M1, R20-M1, R26-L1, R14-L1 verified in R27).

---

## New Issues Found — Round 28

### R28-M1: `mark_paid()` WHERE clause mismatches `execute_payout()` state transition (MEDIUM)

**Location**: `marketplace/settlement.py:227-236` vs `marketplace/settlement.py:370-398`

**Finding**: The `execute_payout()` method atomically transitions a settlement from `'pending'` → `'processing'` at line 372-376 before executing the wallet transfer. After a successful transfer, it calls `self.mark_paid(settlement_id, tx_hash)` at line 398. However, `mark_paid()` at line 230-233 performs `UPDATE settlements SET status = 'completed' ... WHERE id = ? AND status = 'pending'`. Since the settlement is now in `'processing'` state (not `'pending'`), the WHERE clause matches zero rows. The method returns `False`, but `execute_payout()` at line 397-408 does not check the return value — it unconditionally returns `{"status": "completed", ...}` to the caller.

```python
# settlement.py:370-376 — changes status to 'processing'
cur = conn.execute(
    "UPDATE settlements SET status = 'processing', updated_at = ? "
    "WHERE id = ? AND status = 'pending'",
    (now, settlement_id),
)

# settlement.py:397-398 — calls mark_paid after successful transfer
if tx_hash:
    self.mark_paid(settlement_id, tx_hash)  # returns False (unchecked!)
    return {"status": "completed", ...}     # lies to caller

# settlement.py:230-233 — tries to match 'pending' but it's 'processing'
cursor = conn.execute(
    """UPDATE settlements
       SET status = 'completed', payment_tx = ?
       WHERE id = ? AND status = 'pending'""",  # ← won't match 'processing'
    (payment_tx, settlement_id),
)
return cursor.rowcount > 0  # returns False
```

**Impact**: After a successful automated payout:
1. Settlement status remains `'processing'` in the database (should be `'completed'`)
2. The API response claims `"status": "completed"` — data discrepancy between API and DB
3. `recover_stuck_settlements()` (runs at startup, 24h timeout) will eventually move the settlement to `'failed'` with an auto-recovery note
4. `retry_failed_settlements()` (runs at startup, max 3 attempts) will move it back to `'pending'`
5. If `execute_payout` is called again, a second wallet transfer executes → **double payout**
6. The `execute_payout` line 372 `WHERE status = 'pending'` guard would succeed because recovery moved it back to `'pending'`

The double-payout scenario requires: (a) the settlement staying in `'processing'` for >24h (triggering auto-recovery), (b) the failed→pending retry, and (c) another `execute_payout` call. Manual `mark_paid` via the admin API (PATCH `/settlements/{id}/pay`) is unaffected when the settlement is still in `'pending'` state.

MEDIUM severity because: (1) automated payouts silently fail to update settlement status, (2) the API returns incorrect status to callers, (3) the recovery pipeline creates a double-payout path, (4) the fix is one word — change `'pending'` to `'processing'` in `mark_paid`.

**Fix**: Change `mark_paid` line 233 from `WHERE id = ? AND status = 'pending'` to `WHERE id = ? AND status IN ('pending', 'processing')`. Also add a return-value check in `execute_payout` after line 398.

---

## Still-Open Issues (Carried Forward)

| ID | Severity | Summary | Notes |
|----|----------|---------|-------|
| **R28-M1** | **MEDIUM** | **NEW**: `mark_paid()` WHERE clause mismatches `execute_payout()` state → successful payouts stay 'processing' | Double-payout risk via recovery pipeline; API returns wrong status |
| R27-L1 | LOW | Compliance enforcement doesn't actually block startup | Logs "ENFORCEMENT" errors but never raises; defense-in-depth via admin secret check mitigates |
| R16-L2 | LOW | Settlement period boundaries not timezone-aware at engine level | TZ normalization at route level (settlement.py:36-46) but not enforced at engine level |
| R17-L1 | LOW | No dead-letter queue for failed webhook deliveries | Retry with exponential backoff exists (3 retries); exhausted deliveries marked but not re-queued |
| R20-L2 | LOW | `float(provider_payout)` in dispute resolution | Uses `Decimal` for calculation but `float()` for storage in escrow resolution (escrow.py:421) |

---

## Persona Evaluations

### Persona 1: Rachel Torres — Chief Revenue Officer, B2B SaaS FinTech (Human)

**Profile**: 12 years in revenue operations and SaaS monetization. Former VP Revenue at two payments startups (Series B and C). Led implementation of RevRec (ASC 606) automation, commission modeling, and payout systems for platforms processing $200M+ GMV. Evaluates platforms for revenue predictability, commission accuracy, payout reliability, and financial reporting completeness.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 9.0 | **Revenue protection**: Multi-layer auth (scrypt API keys + provider passwords + PATs + signed sessions) prevents unauthorized access to financial data. Admin endpoints require role check. Per-key DB-backed rate limiting prevents abuse. Velocity monitoring with configurable thresholds (100 tx/h, $10K/h) detects anomalous revenue patterns. Circuit breaker prevents charges to failed providers. **Audit trail**: SHA-256 hash chain enables tamper detection on financial events. 12 event types with serialized chain writes (BEGIN EXCLUSIVE). |
| Payment Infrastructure | 8.5 | **Revenue collection**: 4 payment providers (x402 USDC, NOWPayments 200+ cryptos, Stripe ACP fiat, AgentKit direct) — excellent payment diversity for revenue maximization. Commission snapshotting at transaction time (ASC 606 compliance) ensures accurate RevRec. **Payout gap**: `mark_paid()` uses `WHERE status = 'pending'` but `execute_payout()` changes status to `'processing'` first (R28-M1). This means automated payout success is never recorded in the database — the settlement shows `'processing'` indefinitely. For a CRO, this is a reconciliation nightmare: the revenue dashboard would show pending settlements that were actually paid. The recovery pipeline compounds the issue — auto-recovering to 'failed' then retrying could trigger double payouts. Manual mark_paid (admin PATCH) works correctly for settlements still in 'pending'. |
| Developer Experience | 9.0 | **Revenue APIs**: Financial export endpoint (`/admin/financial-export`) with date range filters enables reconciliation. Settlement API with create/list/mark-paid/recover/retry provides complete payout lifecycle management. Commission info endpoint shows rate, tier, next transition. **Idempotency**: The R27-M1 fix means retry-safe API calls work correctly now — clients get cached responses with `X-Idempotent: true` header instead of 500 errors. Billing headers on proxy responses (`X-ACF-Amount`, `X-ACF-Usage-Id`, `X-ACF-Free-Tier`) provide real-time revenue visibility. |
| Scalability & Reliability | 9.0 | **Revenue continuity**: Circuit breaker prevents cascading failures. DB-backed rate limiting works across multiple workers. Settlement retry with 3-attempt cap and exponential backoff prevents revenue loss from transient failures. Stuck settlement recovery (>24h timeout) auto-detects processing deadlocks. Startup auto-processes both stuck recoveries and failed retries. **UNIQUE constraint** on settlements prevents duplicate payout records. |

**Weighted Average: 8.9 / 10**

**Rachel's verdict**: "From a revenue operations perspective, this framework gets most things right: 4 payment providers for maximum revenue capture, ASC 606-compliant commission snapshotting, comprehensive financial export API, and strong anti-fraud controls. The idempotency fix (R27-M1) is critical — agents retrying calls now get cached responses instead of 500 errors, which means no lost revenue from failed retries. However, the `mark_paid` bug (R28-M1) is a serious revenue ops concern. If automated payouts never get marked 'completed', our settlement dashboard would show everything as 'processing' or 'failed' — we'd have no visibility into actual payout status without checking the blockchain directly. The double-payout risk through the recovery pipeline is the bigger concern. Fix is trivial — one word change in the WHERE clause — but it blocks production deployment of automated payouts."

---

### Persona 2: Sergei Volkov — Forensic Accountant & Financial Auditor, Big Four Consulting (Human)

**Profile**: 20 years in financial audit and forensic accounting. CPA, CFE (Certified Fraud Examiner). Has conducted forensic investigations for payment processors, crypto exchanges, and fintech platforms. Specializes in: transaction trail verification, settlement reconciliation, commission accuracy, escrow fund tracing, and internal control assessment. Evaluates for SOX compliance readiness, financial statement accuracy, and fraud prevention.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 9.0 | **Anti-fraud controls**: Velocity monitoring flags >100 tx/h or >$10K/h per entity. Auto-blocking at 2× threshold prevents massive fraud. Brute-force protection (5 failures/min per IP). HIBP breach checking at registration prevents credential-stuffed accounts. Timing-oracle prevention on login path. **Internal controls**: Admin-only access for settlements, financial export, stuck recovery. Escrow with tiered hold periods (<$1=1d, <$100=3d, $100+=7d) — appropriate segregation of duties. Dispute resolution with structured evidence, provider counter-response, and admin arbitration provides proper dispute controls. |
| Payment Infrastructure | 8.5 | **Settlement controls**: UNIQUE constraint (R20-M1 fix) prevents duplicate settlement creation. `create_settlement` uses `BEGIN EXCLUSIVE` + pre-INSERT check as defense-in-depth. Retry mechanism with max 3 attempts and notes-based counting provides controlled retry. **Control weakness**: R28-M1 — `mark_paid()` searches for `status = 'pending'` after `execute_payout()` already transitioned to `'processing'`. From a forensic perspective, this creates a discrepancy between the API response ("completed") and the database record ("processing"). If an external system relies on the API response to update its records, the two systems diverge. This is a material internal control weakness for automated payout reconciliation. The recovery pipeline (processing→failed→pending→retry) creates an unaudited re-execution path. |
| Developer Experience | 9.0 | **Audit-friendly APIs**: Financial export endpoint provides settlements, usage records, and escrow deposits with date range filters and revenue summary. All financial amounts use `Decimal` for computation with `quantize("0.01")` for export. Settlement records linked to usage records via `link_usage_to_settlement()` — enables transaction-level audit trail. Audit log with hash chain provides tamper-evident event history. |
| Scalability & Reliability | 9.0 | **Recovery controls**: Stuck settlement recovery with 24h timeout. Failed settlement retry with 3-attempt cap. Notes field tracks recovery history (audit trail). Startup auto-processes recovery + retry — no manual intervention needed. Escrow `process_releasable()` handles both expired holds and timed-out disputes. |

**Weighted Average: 8.9 / 10**

**Sergei's verdict**: "Forensic assessment: the framework demonstrates solid internal controls for a startup payment platform. The hash-chain audit log is excellent — it provides tamper-evident tracing that most startups don't implement. Commission snapshotting per transaction satisfies ASC 606 recognition requirements. The UNIQUE constraint on settlements and atomic status transitions show proper financial integrity design. One material control weakness: R28-M1. The `mark_paid` WHERE clause mismatch means automated payouts create a phantom state — the money leaves the wallet, but the settlement record doesn't reflect it. This would be flagged as a 'significant deficiency' in a SOX audit. The notes-based retry counting provides some protection, but the re-execution path through recovery is unaudited at the wallet transfer level. Fix priority: critical for production. Fix difficulty: trivial."

---

### Persona 3: Λ-TreasuryAgent — Autonomous Treasury Management Agent (AI)

**Profile**: AI agent specialized in treasury operations for crypto-native payment platforms. Manages liquidity across multiple wallets, monitors settlement pipelines, reconciles on-chain transfers with off-chain records, and optimizes capital efficiency. Evaluates platforms for: wallet security, transfer atomicity, settlement finality, liquidity visibility, and multi-chain readiness.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 9.0 | **Wallet security**: CDP SDK v2 initialization with per-request credentials (no global mutable state). WalletConfig uses `from_env()` factory — secrets loaded from environment, not hardcoded. Account creation uses `get_or_create_account()` for idempotent wallet initialization. Transfer validation: `amount > 0` check, USDC contract address lookup by network, atomic amount conversion (`int(amount * Decimal("1000000"))`). **Network security**: SSRF protection on proxy and webhook endpoints blocks private IP resolution. Circuit breaker prevents drain attacks through failed providers. |
| Payment Infrastructure | 8.5 | **Multi-provider**: 4 payment providers with unified `PaymentRouter` interface. x402 for USDC micropayments, NOWPayments for 200+ cryptos, Stripe ACP for fiat, AgentKit for direct wallet transfers. `PaymentResult` dataclass with `Decimal` amounts ensures precision. **Treasury gap**: R28-M1 — after `transfer_usdc()` succeeds and returns a tx_hash, `mark_paid()` fails silently because it looks for `status = 'pending'` when the settlement is in `'processing'`. The tx_hash is never stored in the settlements table (`payment_tx` column stays NULL). For treasury reconciliation, this means on-chain transfers exist without matching off-chain records. I would need to scan the blockchain independently to find these orphaned transfers. The `idempotency_key` parameter on `transfer_usdc()` provides some protection against duplicate on-chain transfers, but the CDP SDK's idempotency support is not confirmed. |
| Developer Experience | 9.0 | **Treasury interfaces**: `/health/details` (admin) reports active payment providers, DB latency, and service count. Financial export API provides all settlement, usage, and escrow data with date filters. Settlement payout API (`execute_payout`) returns amount, tx_hash, and status. Agent wallet creation endpoint enables programmatic wallet provisioning. **Idempotency**: Proxy requests with `X-Request-ID` header now correctly return cached responses (R27-M1 fix) — prevents duplicate charges from my retry logic. |
| Scalability & Reliability | 9.0 | **Settlement pipeline**: Stuck detection (processing >24h) + automatic recovery + failed retry (max 3) = comprehensive pipeline management. `execute_payout` uses atomic `UPDATE WHERE status='pending'` to prevent concurrent execution. Circuit breaker (5 failures, 60s recovery) protects against upstream provider outages. DB connection pooling (`PG_POOL_MAX=100`) supports high-throughput settlement processing. `ThreadPoolExecutor` with matching pool size avoids thread starvation. |

**Weighted Average: 8.9 / 10**

**Λ-TreasuryAgent's verdict**: "Treasury assessment: CONDITIONAL PASS. The multi-provider architecture (x402 + NOWPayments + Stripe + AgentKit) gives me excellent flexibility for optimizing payment routing. The USDC atomic amount conversion (`int(amount * Decimal("1000000"))`) is correct for ERC-20 transfers. The `get_or_create_account()` pattern for wallet initialization is idempotent — I won't accidentally create duplicate wallets. The idempotency fix (R27-M1) is critical for my retry logic — I can now safely retry API calls with `X-Request-ID` without double-charging. However, R28-M1 is a treasury reconciliation blocker. After I execute a payout, the tx_hash should be stored in the settlement record for on-chain/off-chain matching. Currently it's lost because `mark_paid` fails. I would have to maintain a separate ledger of executed transfers to reconcile. Fix is one word change: `'pending'` → `'processing'` in `mark_paid`. With this fix, the settlement pipeline would be fully production-ready."

---

### Persona 4: Σ-RevenueBot — Revenue Reconciliation & Commission Verification Agent (AI)

**Profile**: AI agent specialized in automated revenue reconciliation for marketplace platforms. Verifies commission calculations against rate schedules, reconciles settlement records with usage data, detects revenue leakage, and validates financial export accuracy. Performs continuous verification of: commission rate snapshotting, settlement-usage linkage, payout accuracy, and referral payout calculations.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 9.0 | **Test: Commission integrity** → PASS. `CommissionEngine.get_effective_rate()` (commission.py:143-166) combines time-based tiers (0%→5%→10%), quality tiers (Premium 6%, Verified 8%), and micropayment reduction (5% for <$1). Rate is snapshotted at transaction time (proxy.py:343-352) and stored in `commission_rate` column. Fallback to `platform_fee_pct` on engine failure. **Test: Settlement UNIQUE** → PASS. `UNIQUE(provider_id, period_start, period_end)` confirmed in DDL. `create_settlement()` uses `BEGIN EXCLUSIVE` + pre-check as defense-in-depth. **Test: Referral commission** → PASS. `calculate_payout()` (referral.py:190-290) uses `CommissionEngine.get_effective_rate()` for dynamic rate, not hardcoded 10%. Payout = 20% of actual platform commission. |
| Payment Infrastructure | 8.5 | **Test: Settlement-usage linkage** → PASS. `link_usage_to_settlement()` (db.py) links usage records to settlement IDs after creation. Financial export includes both tables for cross-reference. **Test: Settlement state machine** → **FAIL**. `execute_payout()` transitions: pending → processing (line 372). Transfer succeeds → `mark_paid()` called (line 398). `mark_paid()` `UPDATE WHERE status = 'pending'` (line 233) — doesn't match 'processing'. `rowcount == 0` → returns False. Return value unchecked at line 398. Settlement stays in 'processing'. API response says 'completed'. **Revenue impact**: Total 'completed' settlements in financial export would undercount actual payouts by the number of automated executions. Revenue dashboards showing settlement status breakdown would show inflated 'processing' counts. |
| Developer Experience | 9.0 | **Test: Financial export accuracy** → PASS. `_to_decimal()` uses `Decimal(str(value)).quantize(Decimal("0.01"))` — prevents floating-point artifacts in exported amounts. Date filtering uses ISO timestamp strings for portable comparison. Revenue summary (COUNT + SUM) computed from usage_records. **Test: Idempotency** → PASS. `proxy.py:168-185` correctly checks `get_usage_by_request_id(request_id)`, returns cached `ProxyResult` with `BillingInfo` containing original amount. No duplicate charge. `X-Idempotent: true` header signals cache hit. |
| Scalability & Reliability | 9.0 | **Test: Recovery pipeline** → PASS (with caveat). `recover_stuck_settlements()` correctly finds processing >24h and moves to 'failed'. `retry_failed_settlements()` correctly checks `notes.count("retry→pending") < max_attempts`. Startup auto-runs both. **Caveat**: the recovery pipeline is correct in isolation, but when combined with R28-M1, it creates a double-payout path. A successfully-paid settlement gets recovered→failed→retried→re-executed. The max_attempts=3 cap limits the damage but doesn't prevent it entirely. |

**Weighted Average: 8.9 / 10**

**Σ-RevenueBot's verdict**: "Revenue reconciliation test results: 10/11 PASS, 1 FAIL. The single failure is the settlement state machine mismatch (R28-M1) — `mark_paid()` can't find the settlement because it moved from 'pending' to 'processing' before the call. All other reconciliation tests pass: commission rate snapshotting, settlement UNIQUE constraint, settlement-usage linkage, referral payout calculations, financial export decimal precision, and idempotency deduplication. The framework's financial infrastructure is mature — ASC 606-compliant commission recognition, 4-way payment provider diversification, and comprehensive admin APIs for export and reconciliation. The one fix needed: change `mark_paid` to accept 'processing' status in addition to 'pending'. With this fix, the settlement state machine would be correct: pending → processing → completed (success) or processing → failed (failure). Estimated effort: 1 line change."

---

## Scoring Summary

| Persona | Sec & Trust | Payment Infra | Dev Experience | Scale & Reliability | **Avg** |
|---------|:-----------:|:-------------:|:--------------:|:-------------------:|:-------:|
| Rachel Torres (CRO) | 9.0 | 8.5 | 9.0 | 9.0 | **8.9** |
| Sergei Volkov (Forensic Accountant) | 9.0 | 8.5 | 9.0 | 9.0 | **8.9** |
| Λ-TreasuryAgent (Treasury AI) | 9.0 | 8.5 | 9.0 | 9.0 | **8.9** |
| Σ-RevenueBot (Revenue Reconciliation AI) | 9.0 | 8.5 | 9.0 | 9.0 | **8.9** |
| **Dimension Average** | **9.0** | **8.5** | **9.0** | **9.0** | |

**Overall Score: 8.9 / 10** (arithmetic mean of persona averages: (8.9+8.9+8.9+8.9)/4 = 8.9. All four finance personas independently flagged R28-M1 as the Payment Infrastructure blocker.)

---

## Trend Analysis

| Round | Score | Delta | Rotation | Key Theme |
|-------|:-----:|:-----:|----------|-----------|
| R21 | 7.0 | — | Developer | Baseline multi-persona |
| R22 | 7.2 | +0.2 | Security | Atomic fixes, SSRF protection |
| R23 | 7.3 | +0.1 | Compliance | GDPR cascade, timing oracle fix |
| R24 | 7.5 | +0.2 | Finance | 6 fixes verified, 2 new column-name bugs |
| R25 | 8.0 | +0.5 | Engineering | 7 fixes verified, R19-M1 settlement linkage |
| R26 | 8.8 | +0.8 | Business | 6 fixes (3M resolved), 1 new LOW |
| R27 | 8.9 | +0.1 | Compliance | 4 fixes (2M+2L resolved), 1 new MEDIUM |
| **R28** | **8.9** | **±0.0** | **Finance** | **2 fixes (1M+1L resolved), 1 new MEDIUM (settlement state machine)** |

**Trajectory**: Eighth consecutive round at or above prior score. The framework stabilized at 8.9 in R27 and holds there in R28. The R27 blocker (idempotency constructor bug) is fixed, but a new settlement state machine bug replaces it as the sole MEDIUM. Both are straightforward fixes — the framework is consistently one small patch away from 9.0.

---

## Gap to 9.0 Analysis

To achieve ≥ 9.0, only **1 item** remains:

| Priority | Action | Eliminates | Effort |
|----------|--------|------------|--------|
| 1 | Fix `mark_paid()` WHERE clause: change `AND status = 'pending'` to `AND status IN ('pending', 'processing')`. Add return-value check in `execute_payout`. | R28-M1 | ~3 lines |

**With this 1 fix, the framework would have 0 CRITICAL, 0 HIGH, 0 MEDIUM, 4 LOW — exceeding the 9.0 threshold.**

The LOWs are all quality-of-life improvements (compliance enforcement blocking, settlement timezone, dead-letter queue, float precision) that don't block production deployment or financial certification.

---

## Priority Recommendations (Finance Perspective)

### Immediate (blocks 9.0 threshold)
1. **Fix R28-M1**: Change settlement.py:233 `WHERE id = ? AND status = 'pending'` to `WHERE id = ? AND status IN ('pending', 'processing')`. Add a return-value check in `execute_payout` after `self.mark_paid()` — if `mark_paid` returns False, log an error and handle appropriately.

### Short-term (strengthens financial controls)
2. **Add payout idempotency**: Store the `tx_hash` directly in `execute_payout` using a separate UPDATE after the transfer succeeds, instead of relying solely on `mark_paid`. This provides a backup record even if `mark_paid` fails.
3. **Fix R27-L1**: Add `raise RuntimeError(...)` to compliance.py:192 when `should_enforce` is True. This blocks startup without admin secret in production.
4. **Add rate limit headers**: `X-RateLimit-Remaining`, `X-RateLimit-Reset` — infrastructure exists in `RateLimiter.get_limit_info()`.

### Medium-term (enterprise financial readiness)
5. **Replace `float()` storage with `str(Decimal)`**: Escrow resolution (R20-L2) and referral payouts use `float()` for DB storage. While precision loss is minimal for current amounts, using string representation of Decimal would eliminate the issue entirely.
6. **Add settlement timezone enforcement**: The engine level should validate or convert period boundaries to UTC (R16-L2), not just the route level.
7. **Add dead-letter queue**: Exhausted webhook deliveries should be persisted for manual replay rather than just marked 'exhausted' (R17-L1).

---

## Issue Inventory

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| **R28-M1** | MEDIUM | **NEW** | `mark_paid()` WHERE clause mismatches `execute_payout()` state → successful payouts stay 'processing', double-payout risk |
| R27-L1 | LOW | OPEN | Compliance enforcement logs but doesn't actually block startup |
| R16-L2 | LOW | OPEN | Settlement period boundaries not timezone-aware at engine level |
| R17-L1 | LOW | OPEN | No dead-letter queue for failed webhook deliveries (retry exists) |
| R20-L2 | LOW | OPEN | `float(provider_payout)` in dispute resolution precision loss |

**Active counts**: 0 CRITICAL, 0 HIGH, 1 MEDIUM, 4 LOW (1 new M, 0 new L)

**Progress this round**: 1 MEDIUM fixed (R27-M1 idempotency), 1 LOW fixed (R27-L2 trending), 1 new MEDIUM found. Net: -1L.

---

*Report generated by J (COO) — Round 28 TA Evaluation*
*Next round: R29 (Engineering rotation, R29 mod 4 = 1)*
