# TA Evaluation Report — Round 25

| Field | Value |
|-------|-------|
| **Result**: **8.0/10** | |
| **Round** | 25 |
| **Date** | 2026-03-25 |
| **Rotation** | Engineering (R25 mod 4 = 1) |
| **Evaluator** | J (COO / Technical Director) |
| **Overall Score** | **8.0 / 10** |
| **Pass Streak** | 0 / 5 (need 5 consecutive ≥ 9.0) |
| **Verdict** | FAIL — below 9.0 threshold |

---

## Executive Summary

Round 25 applies an **Engineering rotation** lens — evaluating the framework through the eyes of a Staff SRE, Platform Architect, Security Pentesting Agent, and CI/CD Validation Bot. This round shows the **largest score improvement** in the evaluation series (+0.5 from R24's 7.5 to 8.0), driven by 4 MEDIUM and 3 LOW fixes verified. Most notably, R19-M1 (settlement↔usage linkage — a long-standing architectural gap since Round 19) is now resolved via a new `settlement_id` column with proper migration. R21-M1 (`credit_balance` refund differentiation) is also fixed. However, the PAT deletion fix for R24-L2 introduced a new wrong-column bug (R25-M1), repeating the exact same pattern as R24-M1. Five MEDIUMs remain open, preventing the 9.0 threshold.

---

## Methodology

- **Code review**: All `marketplace/*.py` (30 files), `api/main.py`, `api/routes/*.py` (27 routes), `payments/*.py` (5 files) read and analyzed
- **Verification**: Each R24 finding independently verified via code inspection + grep (GATE-6 anti-fabrication)
- **Schema cross-reference**: Table schemas verified against DELETE/UPDATE queries in `delete_user_data()`
- **Persona rotation**: Engineering focus — 2 human decision-makers + 2 AI agent personas, each scoring independently

---

## R24 Issue Verification (GATE-6: Independent Re-Run)

| R24 ID | Issue | Status | Evidence |
|--------|-------|--------|----------|
| R24-M1 | `delete_user_data()` wrong column names (`member_id`, `user_id`) | **FIXED** | `db.py:1830-1833` now uses `WHERE agent_id = ?`; `db.py:1841-1845` now uses `WHERE buyer_id = ?` — matches schema at lines 296-301 (`agent_id`) and 355-361 (`buyer_id`) |
| R24-M2 | `check_rate_limit()` thread-unsafe shared state mutation | **FIXED** | `auth.py:186` now passes `rate_override=limit` to `allow()` instead of mutating `self._per_key_rl.rate`. `DatabaseRateLimiter.allow()` (rate_limit.py:132) accepts `rate_override` parameter — no shared state mutation |
| R24-L1 | Audit IP anonymization not operationally automated | **FIXED** | `api/main.py:294-300` now calls `audit_logger.anonymize_old_entries(_retention_days)` during startup, with configurable `ACF_AUDIT_RETENTION_DAYS` env var (default 365) |
| R24-L2 | `delete_user_data()` missing `pat_tokens` cascade | **PARTIAL FIX** | `db.py:1847-1851` adds `DELETE FROM pat_tokens WHERE provider_id = ?` — BUT `pat_tokens` schema (provider_auth.py:517-524) has column `owner_id`, not `provider_id`. Query matches 0 rows. **New bug → R25-M1** |

**Also verified (long-standing issues):**

| ID | Issue | Status | Evidence |
|----|-------|--------|----------|
| R19-M1 | Settlement↔usage_records not linked | **FIXED** | `usage_records` schema now includes `settlement_id TEXT` column (db.py:213). Migration function `_migrate_usage_settlement_id()` (db.py:621-625) adds column to existing tables. `link_usage_to_settlement()` function (db.py:842-856) atomically tags usage records. Called from `create_settlement()` (settlement.py:147-149) |
| R19-L1 / R20-L1 | `recover_stuck_settlements` not exposed via API/cron | **FIXED** | `api/main.py:302-308` calls `settlement_engine.recover_stuck_settlements(timeout_hours=24)` during startup with error handling |
| R21-M1 | `credit_balance` no `is_refund` flag for audit | **FIXED** | `db.py:1659` now checks `is_refund = reason.startswith("refund") or reason.startswith("escrow_refund")`. When `is_refund=True`, `total_deposited` is not incremented (db.py:1663-1664), preventing refunds from inflating deposit totals |
| R16-M1 | No idempotency key for `forward_request` retries | **PARTIAL FIX** | Proxy layer supports `request_id` deduplication (proxy.py:129-141, checks `get_usage_by_request_id`). However, `api/routes/proxy.py` does NOT extract `X-Request-ID` from request headers and pass it to `forward_request()` — the feature is architecturally present but not exposed at the HTTP layer |

---

## Already Fixed Issues (Not Re-Reported)

The following 70+ issues from R1–R24 have been verified as fixed and are excluded from scoring. Notable additions verified this round:

1. R24-M1: `delete_user_data` wrong column names → FIXED (db.py:1831 `agent_id`, 1843 `buyer_id`)
2. R24-M2: Thread-unsafe rate limit mutation → FIXED (auth.py:186 `rate_override=limit`)
3. R24-L1: Audit IP anonymization not automated → FIXED (main.py:294-300)
4. R19-M1: Settlement↔usage_records linkage → FIXED (db.py:213, 842-856; settlement.py:147-149)
5. R19-L1 / R20-L1: Stuck settlement recovery not exposed → FIXED (main.py:302-308)
6. R21-M1: `credit_balance` no refund differentiation → FIXED (db.py:1659-1675)

See R24 report for the complete prior-round fix list (61+ items from R1–R23).

---

## New Issues Found — Round 25

### R25-M1: `delete_user_data()` PAT deletion uses non-existent column `provider_id` (MEDIUM)

**Location**: `marketplace/db.py:1848-1851`

**Finding**: The fix for R24-L2 added PAT token deletion to the GDPR cascade, but the DELETE query references `provider_id` — a column that does not exist in the `pat_tokens` table. The query silently deletes zero rows while the function reports success.

```python
# db.py:1848-1851 — pat_tokens schema has 'owner_id', NOT 'provider_id'
cur = conn.execute(
    "DELETE FROM pat_tokens WHERE provider_id = ?", (user_id,)
)
deleted["pat_tokens_deleted"] = cur.rowcount  # Always 0
```

**Schema evidence** (provider_auth.py:517-524):
```sql
CREATE TABLE IF NOT EXISTS pat_tokens (
    key_id TEXT PRIMARY KEY,
    owner_id TEXT NOT NULL,  -- ← correct column name
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
```

**Root cause**: This is a recurrence of the R24-M1 bug pattern — query column names not validated against table schema. The R24 report's suggested fix text incorrectly used `provider_id` instead of `owner_id`, and the implementation followed the wrong suggestion.

**Impact**: GDPR Article 17 violation — PAT tokens are never deleted during data erasure. An orphaned PAT could theoretically authenticate until its expiry date, creating both a privacy and security gap. From an engineering perspective, this reveals a lack of integration tests covering the deletion path.

**Fix**: Change `provider_id` → `owner_id` in the query.

---

### R25-L1: `delete_user_data()` does not anonymize financial record PIIs in `deposits` and `escrow_holds` (LOW)

**Location**: `marketplace/db.py:1803-1874`

**Finding**: The `delete_user_data()` function anonymizes `usage_records.buyer_id` (line 1814) but does NOT anonymize or delete PII from:
- `deposits` table (`buyer_id` column) — db.py:363-377
- `escrow_holds` table (`buyer_id`, `provider_id` columns)

These tables contain financial records that should be retained for audit but with PII anonymized (matching the `usage_records` pattern).

**Impact**: After GDPR deletion, `deposits.buyer_id` and `escrow_holds.buyer_id` retain the original user ID, creating a data linkage point. LOW severity because these are financial records with potential legal retention requirements, and the user ID alone without API keys provides limited identification.

**Fix**: Add `UPDATE deposits SET buyer_id = '[deleted]' WHERE buyer_id = ?` and similar for `escrow_holds` to the deletion cascade.

---

### R25-L2: Proxy route does not extract `X-Request-ID` to enable idempotency (LOW)

**Location**: `api/routes/proxy.py:106-115`

**Finding**: The proxy layer supports idempotency via `request_id` parameter (proxy.py:129-141), and the CORS configuration accepts `X-Request-ID` headers (main.py:109). However, the proxy route handler does NOT extract the header and pass it to `forward_request()`:

```python
# api/routes/proxy.py:106-115 — no request_id extraction
result = proxy_result = await proxy.forward_request(
    service=service_dict,
    buyer_id=buyer_id,
    method=request.method,
    path=f"/{path}" if path else "",
    headers=dict(request.headers),
    body=body if body else None,
    query_params=dict(request.query_params),
    x402_paid=x402_paid,
    # Missing: request_id=request.headers.get("x-request-id")
)
```

**Impact**: The idempotency mechanism exists but is dead code at the API layer. Retried requests can cause duplicate billing. LOW severity because the underlying mechanism is already built — this is a single-line wiring fix.

**Fix**: Add `request_id=request.headers.get("x-request-id")` to the `forward_request()` call.

---

## Still-Open Issues (Carried Forward)

| ID | Severity | Summary | Notes |
|----|----------|---------|-------|
| R16-M1 | MEDIUM | No idempotency key for proxy retries | PARTIAL: Proxy supports it (proxy.py:129-141), route doesn't wire it (see R25-L2) |
| R17-M1 | MEDIUM | `execute_payout` has no provider-side failure recovery | Settlement moves to 'failed' but no retry mechanism |
| R18-M1 | MEDIUM | Escrow release has no double-spend guard across concurrent calls | Single-instance atomic but no distributed guard |
| R20-M1 | MEDIUM | No distributed lock for settlement creation | Acceptable for MVP single-instance |
| R14-L1 | LOW | No circuit breaker for upstream provider failures | |
| R16-L2 | LOW | Settlement period boundaries not timezone-aware | |
| R17-L1 | LOW | No dead-letter queue for failed webhook deliveries | Retry with exponential backoff exists |
| R18-L1 | LOW | No health check endpoint for dependency monitoring | `/health` exists but doesn't check dependencies |
| R20-L2 | LOW | `float(provider_payout)` in dispute resolution | Uses `Decimal` for calculation but `float()` for storage |

---

## Persona Evaluations

### Persona 1: Kazuki Tanaka — Staff Site Reliability Engineer (Human)

**Profile**: 14 years in SRE at high-traffic fintech platforms. Responsible for production readiness, incident response, operational observability, and system recovery. Evaluates platforms for operational hygiene, failure modes, and "3 AM production incident" readiness.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.0 | Scrypt with OWASP parameters, HMAC-SHA256 webhooks, audit hash chain with tamper detection — all solid operational security foundations. SSRF protection on both proxy and webhook endpoints prevents internal network exfiltration. Timing oracle prevention for auth is the kind of detail that shows security maturity. Deduction: PAT deletion bug (R25-M1) means orphaned authentication tokens survive user deletion — an operational security gap. |
| Payment Infrastructure | 8.0 | Settlement↔usage linkage (R19-M1 fix) is a **major** operational improvement — I can now trace any settlement amount back to its constituent transactions. Stuck settlement recovery runs on startup (main.py:302-308). Tiered escrow holds with tiered dispute timeouts show operational sophistication. Deduction: No distributed lock means concurrent settlement runs could cause issues, but acceptable for single-instance MVP. |
| Developer Experience | 8.0 | Clean factory pattern in `_init_components()` (main.py:155-233) — all dependencies injected, testable. Protocol-based rate limiter interface enables swapping backends. Financial export endpoint with date filtering gives operational teams the data they need. `recover_stuck_settlements` being automated is exactly what I'd want to see. |
| Scalability & Reliability | 7.5 | DB-backed rate limiter enables horizontal scaling. ThreadPoolExecutor for async DB access avoids event loop blocking. BUT: no circuit breaker for upstream provider failures (R14-L1) means a failing provider can cascade. `recover_stuck_settlements` only runs at startup, not periodically — if a settlement gets stuck mid-operation, it waits until the next restart. No structured error alerting beyond logging. |

**Weighted Average: 7.9 / 10**

**Kazuki's verdict**: "This is the first round where I'd call the system operationally viable. Settlement↔usage traceability was the missing piece for incident investigation — if a provider disputes a payout amount, I can now join on `settlement_id` to reconstruct the exact transaction set. The stuck settlement recovery is good but should run on a periodic schedule, not just at startup. The PAT token deletion bug is concerning from an access-revocation standpoint — it means 'delete my data' doesn't actually revoke all authentication tokens."

---

### Persona 2: Sarah Chen — Principal Platform Architect (Human)

**Profile**: 18 years designing distributed systems at scale. Led architecture for three marketplace platforms processing $500M+ GMV. Evaluates codebases for modularity, extensibility, database portability, and architectural debt.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.0 | Multi-layer authentication architecture: scrypt API keys + scrypt provider passwords + HMAC session tokens + PAT tokens. Each layer has appropriate security properties. Provider Auth includes HIBP breach checking — proactive security beyond the minimum. `secrets.compare_digest()` and `hmac.compare_digest()` used consistently for timing-safe comparison. |
| Payment Infrastructure | 8.5 | The Payment Provider abstraction (payments/base.py) with ABC is textbook — clean interface segregation. PaymentRouter (payments/router.py) is elegant: case-insensitive lookup, list/get/route, proper `__len__`/`__contains__` protocol support. 4 providers (x402, NOWPayments, Stripe ACP, AgentKit) demonstrate the abstraction works in practice. Commission engine with time-based + quality-based + micropayment tiers is genuinely sophisticated for an MVP. Settlement now links to usage records — the data model is architecturally sound. |
| Developer Experience | 8.5 | Exemplary module organization: 30 marketplace modules with clear single-responsibility. 27 API route modules, each focused on a domain. `Protocol`-based rate limiter interface (rate_limit.py:19-23) enables backend swapping without touching consumers. `create_rate_limiter()` factory (rate_limit.py:231-251) is the right pattern. Database abstraction layer supporting both SQLite and PostgreSQL with `_to_pg_sql()` translation shows portability awareness. Immutable dataclasses used consistently for value objects (`CommissionTier`, `QualityTier`, `VelocityAlert`, `WebhookSubscription`). |
| Scalability & Reliability | 7.5 | The SQLite↔PostgreSQL dual-backend is well-engineered but `BEGIN EXCLUSIVE` → `BEGIN` translation (db.py:53) drops from serializable to read-committed isolation on PostgreSQL. This means every financial operation that relies on exclusive locking (balance deduction, free tier claims, audit chain) would need rearchitecting for PG. The `ThreadPoolExecutor` pattern works but is a leaky abstraction — proper async PG support via `asyncpg` would be the production path. No distributed locking for settlements (R20-M1) blocks multi-instance deployment. |

**Weighted Average: 8.1 / 10**

**Sarah's verdict**: "This is one of the more architecturally mature MVP codebases I've reviewed. The Payment Provider abstraction is clean and extensible — adding a fifth payment provider would require zero changes to the router or proxy layers. The settlement↔usage linkage fix resolves what was the biggest architectural gap. The commission engine with three-tier logic (time + quality + micropayment) shows product-level thinking embedded in the architecture. My main concern is the SQLite→PG transition path: the `BEGIN EXCLUSIVE` translation is a known debt item that will require careful rework for production horizontal scaling."

---

### Persona 3: Λ-PenTestScanner — Automated Security Penetration Testing Agent (AI)

**Profile**: AI agent specialized in automated security assessment of web APIs and payment systems. Runs static analysis, fuzzes input boundaries, traces authentication flows, and identifies cryptographic weaknesses. Evaluates frameworks against OWASP Top 10 and PCI-DSS relevant controls.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.5 | **Authentication layer**: Scrypt (N=16384, r=8, p=1, dklen=32) with random 16-byte salt — exceeds OWASP minimums. Legacy SHA-256 migration path uses `secrets.compare_digest()` for constant-time comparison. Timing oracle prevention via pre-computed `_DUMMY_HASH` (provider_auth.py:73) — response time is indistinguishable between "user not found" and "wrong password" paths. **SSRF protection**: Comprehensive on both proxy (proxy.py:147-168) and webhooks (webhooks.py:113-134, 282-305) — blocks private, loopback, link-local, and reserved IPs. Configurable `ACF_INTERNAL_HOSTS` allowlist for platform-owned services. Evidence URL validation enforces `https://` scheme only (escrow.py:44-70). **Session management**: HMAC-SHA256 signed cookies with derived key (provider_auth.py:160-162) — purpose-specific key derivation from master secret. 24h max age. **Deduction**: PAT deletion bug (R25-M1) means orphaned tokens survive user deletion and remain valid until expiry — a credential revocation gap. |
| Payment Infrastructure | 8.0 | Balance deduction uses `BEGIN EXCLUSIVE` for atomicity (db.py:1537). Free tier claiming uses atomic INSERT within exclusive transaction (proxy.py:80-106) preventing race-condition abuse. Escrow state machine enforces valid transitions: only `held` → `release`/`dispute`, only `disputed` → `resolve`. `partial_refund` validates 0 < amount < hold (escrow.py:387-398). Webhook payloads signed with HMAC-SHA256 (webhooks.py:374-378). **Deduction**: No distributed lock on settlements means concurrent payout attempts possible under specific timing (R20-M1). |
| Developer Experience | 7.5 | From a security perspective: error messages are appropriately generic (AuthError: "Invalid API key" — doesn't distinguish missing vs wrong). Admin endpoints require secret validation. Global exception handler (main.py:386-393) returns generic "Internal server error" without stack traces. Security headers middleware (main.py:339-358) includes HSTS, CSP, X-Frame-Options, Referrer-Policy — comprehensive. Compliance check runs at startup and can enforce critical checks in production mode. |
| Scalability & Reliability | 8.0 | IP-level rate limiting (60/min) + per-key rate limiting (configurable per key) provides defense-in-depth against brute force. DB-backed rate limiter prevents distributed brute force across multiple IPs targeting the same key. Velocity monitoring (velocity.py) detects anomalous transaction patterns with configurable thresholds. `should_block_transaction()` triggers at 2x threshold — reasonable circuit-breaker for fraud prevention. Password strength validation + HIBP breach checking at registration blocks weak credentials proactively. |

**Weighted Average: 8.0 / 10**

**Λ-PenTestScanner's verdict**: "Security assessment: PASS WITH NOTES. The authentication and authorization layers are well-implemented with industry-standard algorithms and proper timing-safe comparisons throughout. SSRF protection is comprehensive and consistent across all outbound request paths. The most significant finding is R25-M1 (PAT deletion wrong column): this creates a credential revocation gap where a user's Personal Access Tokens survive GDPR deletion. While the tokens will eventually expire naturally (configurable via ACF_PAT_EXPIRY_DAYS, default 90), the window between deletion request and natural expiry represents an unauthorized access risk. Recommendation: fix R25-M1 and add an integration test that verifies actual row deletion across all tables in the GDPR cascade."

---

### Persona 4: Σ-BuildValidator — CI/CD Pipeline Validation Agent (AI)

**Profile**: AI agent responsible for build validation, test coverage analysis, schema migration verification, and deployment readiness scoring. Evaluates codebases for automated quality assurance readiness and continuous deployment fitness.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 7.5 | Compliance check (compliance.py) runs at startup and can enforce critical checks (`ACF_ENFORCE_COMPLIANCE=true`). However, compliance enforcement only blocks critical failures, not warnings — in a CI/CD pipeline, I'd want warnings to fail the build too. No automated security scanning (SAST/DAST) integration visible. Secret management via environment variables is standard but no validation of secret strength/format at build time. |
| Payment Infrastructure | 8.0 | Schema migration for `settlement_id` column (db.py:621-625) uses `ALTER TABLE` with error handling — safe for incremental deployments. Payment provider initialization (main.py:120-152) uses graceful degradation: missing credentials log info-level messages and skip, rather than crashing. This is CI/CD-friendly — the app can start in any environment configuration. |
| Developer Experience | 8.0 | Component factory `_init_components()` (main.py:155-233) returns a dict of all dependencies — excellent for test fixtures. Clean separation between initialization (module-level) and startup (event handler) prevents import-time side effects. 30+ marketplace modules average under 300 lines each — well within the 800-line file size guideline. Protocol-based interfaces enable mock injection for tests. However: no visible test directory, no pytest configuration, no CI/CD pipeline definition — automated quality assurance infrastructure is absent from the repository. |
| Scalability & Reliability | 7.5 | `ALTER TABLE` migrations in db.py work for SQLite but are fragile for PostgreSQL (no versioned migration framework like Alembic). No health check for database connectivity (the `/health` endpoint exists but doesn't verify DB connection). No graceful shutdown handler — in-flight settlements could be interrupted. The startup sequence runs recovery (stuck settlements, IP anonymization) which is good operational hygiene, but if these fail, only a warning is logged rather than preventing startup. |

**Weighted Average: 7.8 / 10**

**Σ-BuildValidator's verdict**: "Build readiness assessment: CONDITIONAL PASS. The codebase is structurally sound with clean module boundaries and proper dependency injection via factory functions. Schema migrations exist but use ad-hoc `ALTER TABLE` rather than a versioned migration framework — this creates deployment risk at scale. The most significant gap for CI/CD readiness is the apparent absence of automated tests: no test directory, no pytest.ini/pyproject.toml test configuration, no test fixtures or conftest.py visible in the codebase. Without tests, every deployment is a manual verification exercise. The GDPR deletion path is a prime example of where integration tests would have caught both R24-M1 and R25-M1 before they reached production."

---

## Scoring Summary

| Persona | Sec & Trust | Payment Infra | Dev Experience | Scale & Reliability | **Avg** |
|---------|:-----------:|:-------------:|:--------------:|:-------------------:|:-------:|
| Kazuki Tanaka (Staff SRE) | 8.0 | 8.0 | 8.0 | 7.5 | **7.9** |
| Sarah Chen (Platform Architect) | 8.0 | 8.5 | 8.5 | 7.5 | **8.1** |
| Λ-PenTestScanner (AI) | 8.5 | 8.0 | 7.5 | 8.0 | **8.0** |
| Σ-BuildValidator (AI) | 7.5 | 8.0 | 8.0 | 7.5 | **7.8** |
| **Dimension Average** | **8.0** | **8.1** | **8.0** | **7.6** | |

**Overall Score: 8.0 / 10** (arithmetic mean of persona averages: (7.9+8.1+8.0+7.8)/4 = 7.95 ≈ 8.0)

---

## Trend Analysis

| Round | Score | Delta | Rotation | Key Theme |
|-------|:-----:|:-----:|----------|-----------|
| R21 | 7.0 | — | Developer | Baseline multi-persona |
| R22 | 7.2 | +0.2 | Security | Atomic fixes, SSRF protection |
| R23 | 7.3 | +0.1 | Compliance | GDPR cascade, timing oracle fix |
| R24 | 7.5 | +0.2 | Finance | 6 fixes verified, 2 new column-name bugs |
| **R25** | **8.0** | **+0.5** | **Engineering** | **7 fixes verified (incl. R19-M1 settlement linkage), 1 new column-name bug** |

**Trajectory**: Strongest improvement in the series (+0.5). Crossed the 8.0 threshold for the first time. The R19-M1 fix (settlement↔usage linkage) resolved the framework's most significant architectural gap. The recurring column-name bug pattern (R24-M1 → R25-M1) suggests the GDPR deletion path needs an automated schema-validation test.

---

## Gap to 9.0 Analysis

To achieve ≥ 9.0 (≤ 3 MEDIUM, good DX, production-ready patterns), the following is needed:

| Priority | Action | Eliminates |
|----------|--------|------------|
| 1 | Fix R25-M1: `provider_id` → `owner_id` in PAT deletion + add integration test | R25-M1 |
| 2 | Wire `X-Request-ID` through proxy route to enable idempotency | R16-M1 (completes partial fix), R25-L2 |
| 3 | Add provider-side failure recovery for `execute_payout` (retry with idempotency key) | R17-M1 |
| 4 | Add distributed lock or optimistic concurrency for escrow release | R18-M1 |
| 5 | Add distributed lock for settlement creation (advisory lock or optimistic check) | R20-M1 |

Items 1-2 are one-line fixes. Items 3-5 are architectural improvements that could be deferred for single-instance deployment.

**Fastest path to 9.0**: Fix R25-M1 + wire idempotency (R16-M1/R25-L2) + one of R17-M1/R18-M1/R20-M1, reducing MEDIUMs from 5 to ≤ 3.

---

## Priority Recommendations (Engineering Perspective)

### Immediate (blocks next-round 9.0 attempt)
1. **Fix R25-M1**: Change `provider_id` → `owner_id` in PAT deletion query (db.py:1849). Add an integration test that runs `delete_user_data()` against a populated database and verifies actual row counts.
2. **Wire idempotency** (R16-M1 + R25-L2): Add `request_id=request.headers.get("x-request-id")` to the proxy route call — one-line fix that activates an already-built feature.

### Short-term (blocks production deployment)
3. **Add a versioned migration framework** (Alembic or equivalent) to replace ad-hoc `ALTER TABLE` migrations. Current approach is fragile for multi-instance deployments where migration ordering matters.
4. **Add a GDPR deletion integration test** that creates records in ALL user-facing tables, runs `delete_user_data()`, and verifies that all PII is either deleted or anonymized.

### Medium-term (blocks horizontal scaling)
5. **Distributed settlement lock** (R20-M1): Use PostgreSQL advisory locks (`pg_advisory_lock`) or an optimistic-concurrency version column.
6. **Periodic stuck settlement recovery**: Schedule `recover_stuck_settlements()` to run every 15 minutes, not just at startup.
7. **Circuit breaker for upstream providers** (R14-L1): Implement a simple state machine (closed/open/half-open) per provider endpoint.

---

## Issue Inventory

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| **R25-M1** | MEDIUM | **NEW** | `delete_user_data()` PAT deletion uses `provider_id` instead of `owner_id` |
| R16-M1 | MEDIUM | PARTIAL | Idempotency exists in proxy, not wired at API route level |
| R17-M1 | MEDIUM | OPEN | No provider-side failure recovery in payouts |
| R18-M1 | MEDIUM | OPEN | No double-spend guard on escrow release (distributed) |
| R20-M1 | MEDIUM | OPEN | No distributed lock for settlement creation |
| **R25-L1** | LOW | **NEW** | `delete_user_data` doesn't anonymize `deposits.buyer_id` / `escrow_holds.buyer_id` |
| **R25-L2** | LOW | **NEW** | Proxy route doesn't pass `X-Request-ID` to enable idempotency |
| R14-L1 | LOW | OPEN | No circuit breaker for upstream provider failures |
| R16-L2 | LOW | OPEN | Settlement period boundaries not timezone-aware |
| R17-L1 | LOW | OPEN | No dead-letter queue for failed webhook deliveries |
| R18-L1 | LOW | OPEN | No health check endpoint for dependency monitoring |
| R20-L2 | LOW | OPEN | `float(provider_payout)` in dispute resolution precision |

**Active counts**: 0 CRITICAL, 0 HIGH, 5 MEDIUM (1 new, 1 partially fixed), 8 LOW (2 new)

**Progress this round**: 4 MEDIUM fixed (R24-M1, R24-M2, R19-M1, R21-M1), 3 LOW fixed (R24-L1, R19-L1, R20-L1), 1 new MEDIUM

---

*Report generated by J (COO) — Round 25 TA Evaluation*
*Next round: R26 (Business rotation, R26 mod 4 = 2)*
