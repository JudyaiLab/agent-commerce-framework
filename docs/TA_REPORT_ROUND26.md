# TA Evaluation Report — Round 26

| Field | Value |
|-------|-------|
| **Round** | 26 |
| **Date** | 2026-03-25 |
| **Rotation** | Business (R26 mod 4 = 2) |
| **Evaluator** | J (COO / Technical Director) |
| **Overall Score** | **8.5 / 10** |
| **Pass Streak** | 0 / 5 (need 5 consecutive ≥ 9.0) |
| **Verdict** | FAIL — below 9.0 threshold |

---

## Executive Summary

Round 26 delivers the **strongest single-round improvement** in the evaluation series: **7 fixes verified** (3 MEDIUM + 4 LOW), reducing active issues from 5M+7L to **3M+3L**. Most notably:

- **R18-M1** (escrow double-spend guard) is **independently verified as safe** — the existing `UPDATE WHERE status='held'` + rowcount check provides row-level atomicity in both SQLite and PostgreSQL READ COMMITTED mode. Resolved without code changes.
- **R16-M1** (idempotency not wired) is **fully resolved** — `X-Request-ID` now flows end-to-end from HTTP header through proxy route to usage deduplication.
- **R25-M1** (PAT deletion wrong column) is fixed — `owner_id` now matches schema.
- **R14-L1** (no circuit breaker) is fixed — new `_CircuitBreaker` class in proxy.py with closed→open→half-open pattern.
- **R18-L1**, **R25-L1**, **R25-L2** all fixed (health check, GDPR anonymization gaps).

However, **1 new MEDIUM discovered**: `AgentKitProvider.create_payment()` passes `idempotency_key` to `WalletManager.transfer_usdc()` which does not accept that parameter — causing a `TypeError` at runtime on every AgentKit payment.

Active issue counts now at 0C · 0H · 3M · 3L. The 3 MEDIUM count is AT the ≤3 threshold for 9.0, but the severity of R26-M1 (runtime crash on a primary payment path) keeps the score below that mark.

---

## Methodology

- **Code review**: All `marketplace/*.py`, `api/main.py`, `api/routes/*.py`, `payments/*.py` read and analyzed
- **Verification**: Each R25 finding independently verified via `grep` + code inspection (GATE-6 anti-fabrication)
- **PostgreSQL concurrency analysis**: R18-M1 escrow pattern verified against PostgreSQL READ COMMITTED row-locking behavior
- **Cross-module call-chain tracing**: Discovered R26-M1 by tracing `agentkit_provider.py:178` → `wallet.py:125` method signature mismatch
- **Persona rotation**: Business focus — 2 human decision-makers + 2 AI agent personas, each scoring independently

---

## R25 Issue Verification (GATE-6: Independent Re-Run)

| R25 ID | Sev | Issue | Status | Evidence |
|--------|-----|-------|--------|----------|
| R25-M1 | M | `delete_user_data()` PAT deletion uses wrong column | **FIXED** | `db.py:1849` — `DELETE FROM pat_tokens WHERE owner_id = ?` matches `pat_tokens` schema (`owner_id TEXT NOT NULL`) |
| R16-M1 | M | Idempotency exists in proxy but not wired at API route | **FULLY FIXED** | `api/routes/proxy.py:104` extracts `request_id = request.headers.get("x-request-id")`; `:118` passes to `forward_request()` → `get_usage_by_request_id()` dedup (proxy.py:129-141). End-to-end operational. |
| R18-M1 | M | Escrow release has no double-spend guard across concurrent calls | **RESOLVED** | `escrow.py:194-201`: `UPDATE escrow_holds SET status = 'released' WHERE id = ? AND status = 'held'` + rowcount check. In PostgreSQL READ COMMITTED, concurrent UPDATEs on the same row trigger row-level locking — second transaction re-evaluates WHERE after first commits. Only one caller succeeds; other gets rowcount=0 → EscrowError. Same pattern in `process_releasable()` dispute auto-resolution (escrow.py:507-517). SQLite even safer due to exclusive write locking. Valid distributed double-spend guard. |
| R14-L1 | L | No circuit breaker for upstream provider failures | **FIXED** | `proxy.py:40-73` — `_CircuitBreaker` class (threshold=5, recovery=60s, closed→open→half-open). Wired at `:104`, checked at `:273`, success/failure recorded at `:316-325, 329`. |
| R18-L1 | L | Health check does not verify dependencies | **FIXED** | `health.py:286-299` — `/health` executes `SELECT 1` against DB, returns `{"status": "ok"/"degraded", "database": "ok"/"error"}`. Extended `/health/details` (admin-only, `:302-356`) adds DB latency, service count, payment providers. |
| R25-L1 | L | GDPR cascade misses deposits/escrow_holds | **FIXED** | `db.py:1867-1878` — deposits and escrow_holds `buyer_id` anonymized to `'[deleted]'`. Provider accounts use `f"[deleted-{user_id}]"` for email (UNIQUE-safe, `:1882-1884`). |
| R25-L2 | L | Proxy route doesn't extract X-Request-ID | **FIXED** | `api/routes/proxy.py:104` — header extracted and passed through at `:118`. |

**Verification method:** Independent grep + code read of each fix location (GATE-6 anti-fabrication).

---

## Already Fixed Issues (Not Re-Reported)

The following issues from R1–R25 have been verified as fixed and are excluded from scoring. Notable additions this round:

1. R18-M1: Escrow double-spend guard → RESOLVED (PG row-level locking is a valid guard)
2. R25-M1: `delete_user_data` PAT deletion wrong column → FIXED (db.py:1849 `owner_id`)
3. R16-M1: Idempotency not wired at API layer → FULLY FIXED (proxy route:104+118)
4. R14-L1: No circuit breaker → FIXED (proxy.py:40-73 `_CircuitBreaker`)
5. R18-L1: Health check doesn't verify dependencies → FIXED (health.py:286-299)
6. R25-L1: deposits/escrow_holds not anonymized → FIXED (db.py:1867-1878)
7. R25-L2: Proxy route doesn't extract X-Request-ID → FIXED (proxy.py:104)

See R25 report for the complete prior-round fix list.

---

## New Issues Found — Round 26

### R26-M1: AgentKit `idempotency_key` parameter mismatch — TypeError at runtime (MEDIUM)

**Location:** `payments/agentkit_provider.py:178-182` → `marketplace/wallet.py:125-129`

**Finding:** `AgentKitProvider.create_payment()` passes an `idempotency_key` keyword argument to `WalletManager.transfer_usdc()`, but the wallet method does not accept this parameter:

```python
# agentkit_provider.py:178-182 — CALLER
tx_hash = await self._wallet.transfer_usdc(
    to_address=to_address,
    amount=amount,
    idempotency_key=idempotency_key,  # ← NOT accepted
)
```

```python
# wallet.py:125-129 — CALLEE (no idempotency_key param)
async def transfer_usdc(
    self,
    to_address: str,
    amount: Decimal,
) -> Optional[str]:
```

**Impact:** Every payment through the AgentKit provider raises `TypeError: transfer_usdc() got an unexpected keyword argument 'idempotency_key'`. This blocks the primary crypto payment path for agent-native USDC transfers on Base network. The x402 and NOWPayments paths are unaffected.

**MEDIUM severity because:** (1) runtime crash, not silent failure — the error is immediately visible; (2) only affects AgentKit payment provider, not x402/NOWPayments/Stripe; (3) straightforward fix — either add `idempotency_key: Optional[str] = None` parameter to `wallet.py:transfer_usdc()` and pass to CDP SDK, or remove the kwarg from caller if CDP SDK doesn't support it; (4) AgentKit is the newest payment provider and may not be the primary path for early users.

**Fix options:**
1. Add `idempotency_key: Optional[str] = None` to `WalletManager.transfer_usdc()` and pass to CDP `account.transfer()` if supported
2. Remove `idempotency_key=idempotency_key` from the caller at agentkit_provider.py:181 if CDP SDK handles idempotency internally

---

## Still-Open Issues (Carried Forward)

| ID | Severity | Summary | Since | Notes |
|----|----------|---------|-------|-------|
| **R26-M1** | MEDIUM | AgentKit `idempotency_key` TypeError — blocks AgentKit payments | **R26** | **NEW** — 30-min fix |
| R17-M1 | MEDIUM | No automatic retry for failed settlements | R17 | `execute_payout`: pending→processing→completed/failed. `recover_stuck_settlements()` handles processing>24h. No failed→pending retry. Admin must re-trigger. |
| R20-M1 | MEDIUM | No distributed lock for settlement creation (TOCTOU gap) | R20 | `BEGIN EXCLUSIVE` is serializable in SQLite but translates to `BEGIN` (READ COMMITTED) in PostgreSQL. Concurrent `create_settlement()` calls could create duplicates. Fix: add `UNIQUE(provider_id, period_start, period_end)`. |
| R16-L2 | LOW | Settlement period boundaries not timezone-aware | R16 | |
| R17-L1 | LOW | No dead-letter queue for failed webhook deliveries | R17 | Exponential backoff retry exists (3 attempts, 1→2→4 min) |
| R20-L2 | LOW | `float(provider_payout)` in dispute resolution precision | R20 | Uses `Decimal` for calc but `float()` for DB storage |

**Active counts:** 0 CRITICAL · 0 HIGH · 3 MEDIUM · 3 LOW

---

## Persona Evaluations

### Rotation: Business (2 Human + 2 AI)

---

### Persona 1: Rachel Park — VP Product, B2B SaaS Marketplace (Human)

**Profile:** 12 years in marketplace product management. Led API marketplace products at a Fortune 500 company. Evaluates platforms for enterprise procurement readiness — cares about compliance, audit trails, vendor lock-in risk, and go-to-market readiness.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.8 | Multi-layer auth (scrypt API keys + provider passwords + PATs + signed sessions) covers all user types. SSRF protection on proxy + webhooks prevents the most common marketplace abuse vector. Audit hash chain with SHA-256 tamper detection is enterprise-grade. GDPR cascade now covers 11 tables comprehensively — deposits, escrow, provider accounts all properly anonymized with UNIQUE-safe email handling. Escrow double-spend guard verified as safe via PostgreSQL row-level locking. Compliance check at startup enforces 6 controls in production. HIBP breach checking on provider registration is a strong trust signal. |
| Payment Infrastructure | 8.0 | Four payment providers (x402, NOWPayments, Stripe ACP, AgentKit) is excellent breadth. Dynamic commission engine (0%→5%→10% + quality tiers + micropayment reduction) is genuinely innovative. End-to-end idempotency via X-Request-ID now fully wired. Settlement↔usage linkage provides audit trail for finance teams. **Deduction:** R26-M1 TypeError blocks the AgentKit payment path entirely — a runtime crash on a primary provider is unacceptable for procurement sign-off. Settlement retry gap (R17-M1) means failed payouts need manual intervention. |
| Developer Experience | 9.0 | The proxy-first architecture is the RIGHT design decision — buyers get a single proxy URL, no payment SDK required. 27 route modules covering auth, proxy, settlement, discovery, escrow, webhooks, admin, billing, referral, SLA, batch, financial_export. MCP tool descriptors + `/.well-known/llms.txt` for agent-native discovery. Enhanced search with trending/recommendations creates marketplace dynamics. Free tier with atomic claiming. Financial export endpoint for reconciliation. Circuit breaker (new) adds operational visibility. |
| Scalability & Reliability | 8.3 | Health check now verifies DB connectivity and reports latency. DB-backed rate limiting enables horizontal scaling. Stuck settlement recovery at startup. Velocity monitoring (100 tx/h, $10K/h) for fraud detection. Circuit breaker prevents cascade failures. **Deduction:** Settlement TOCTOU gap (R20-M1) in PostgreSQL mode. No automatic payout retry (R17-M1). Both are single-instance safe but block multi-instance deployment. |

**Weighted Average: 8.5 / 10**

**Rachel's verdict:** "The security and developer experience are enterprise-grade. The audit hash chain and comprehensive GDPR cascade would pass our compliance review. The commission engine is the most sophisticated I've seen in the API marketplace space — it's not just a fee, it's a growth mechanism. But I can't sign off with a broken payment provider — R26-M1 is a procurement blocker. Fix that 30-minute TypeError, add the settlement UNIQUE constraint, and this goes on our shortlist."

---

### Persona 2: Marcus Chen — CEO, AI Agent Startup (Human, Series A)

**Profile:** Technical founder building autonomous trading agents. Needs a marketplace where his agents can discover, call, and pay for APIs without human intervention. Currently evaluating agent-native commerce infrastructure.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.5 | Proxy Key abstraction is exactly right — my agents never see provider API keys. Escrow system verified as concurrency-safe — important when multiple agents might settle the same hold simultaneously. HIBP on provider registration reduces supply-side risk. PAT tokens with 90-day expiry work for agent credential rotation. Velocity monitoring catches runaway agents before they drain wallets. |
| Payment Infrastructure | 7.8 | USDC on Base via x402 is what we want for agent wallets. NOWPayments adds 200+ crypto options. Micropayment rate (5% for <$1) makes per-call economics viable — a $0.01 API call at 10% commission kills our margins, but 5% works. **Deduction:** R26-M1 means AgentKit — the most agent-native payment method (direct wallet-to-wallet USDC) — crashes on every payment. This is our primary integration path. x402 works as a fallback but requires HTTP 402 protocol support. Settlement retry gap means if an agent's payout fails, no one notices until an admin checks. |
| Developer Experience | 8.8 | MCP registry for service discovery is the killer feature — my agents find APIs without hardcoded catalogs. `/.well-known/llms.txt` tells agents what the platform does. The `/proxy/{service_id}/{path}` pattern is beautifully simple. End-to-end idempotency via X-Request-ID means my retry-happy agents won't double-pay. Trending/recommendations help agents pick quality services dynamically. Batch endpoint enables bulk operations. |
| Scalability & Reliability | 8.2 | Circuit breaker prevents cascade when upstream providers go down — essential for autonomous agents. DB-backed rate limiting scales horizontally. Stuck settlement recovery handles processing timeouts. **Deduction:** My fleet of 50+ agents hitting the proxy concurrently needs the settlement TOCTOU gap fixed (R20-M1) before I deploy to production. |

**Weighted Average: 8.3 / 10**

**Marcus's verdict:** "This is the closest thing to what we need — true agent-to-agent commerce infrastructure. The MCP discovery + Proxy Key + per-call micropayment model is the right architecture. The escrow verification is reassuring — I was worried about concurrent settlement from multiple agents. But my agents would hit the AgentKit TypeError on their first payment. Fix that, and I'd start integrating this week. The x402 fallback works, but wallet-to-wallet via AgentKit is what we really want for autonomous operation."

---

### Persona 3: Ω-EnterpriseBD — Enterprise Business Development Agent (AI)

**Profile:** AI agent evaluating B2B platforms for enterprise integration partnerships. Analyzes API documentation, security posture, integration complexity, compliance readiness, and financial reconciliation capabilities. Reports to VP of Partnerships.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 8.8 | ANALYSIS: Platform implements defense-in-depth — input validation at boundaries (SSRF, SQL parameterization), cryptographic integrity (HMAC-SHA256 webhooks, SHA-256 audit hash chain), data lifecycle management (11-table GDPR cascade with UNIQUE-safe email handling). Runtime compliance check validates 6 controls at startup; `ACF_ENFORCE_COMPLIANCE=true` blocks launch on failures. Escrow double-spend guard verified via PostgreSQL row-level locking — satisfies concurrent-access safety requirements. Security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy) are comprehensive. ASSESSMENT: Meets baseline SOC2 CC6.1 requirements. |
| Payment Infrastructure | 8.2 | ANALYSIS: Multi-provider payment routing (4 providers) provides vendor diversity for enterprise risk mitigation. Financial export endpoint enables date-filtered JSON reconciliation. Settlement↔usage linkage provides full transaction traceability. Dispute system with structured categories (6 types), evidence URLs (https-only, max 10), counter-response, and admin arbitration meets commercial dispute requirements. RISK: R26-M1 blocks AgentKit crypto path — enterprise agents requiring direct USDC settlement would fail. Settlement duplicate prevention in PostgreSQL (R20-M1) is needed for multi-instance deployment. |
| Developer Experience | 8.5 | ANALYSIS: 27 route modules across auth, proxy, settlement, identity, reputation, discovery, teams, webhooks, admin, audit, billing, provider, email, referral, portal, agent_provider, escrow, SLA, service_report, batch, financial_export, legal. MCP Tool Descriptor compliance enables zero-config discovery. Protocol-based interfaces (`RateLimiterProtocol`, `PaymentProvider` ABC) enable custom backend integration. i18n support (5 locales). GAP: No generated SDK, no per-endpoint rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`). |
| Scalability & Reliability | 8.0 | ANALYSIS: DB-backed sliding window rate limiting (per-IP + per-key) supports horizontal scaling. Circuit breaker (threshold=5, recovery=60s) prevents cascade failures. Health monitoring at `/health` (DB connectivity) + `/health/details` (admin: latency, services, payment providers). Stuck settlement recovery at startup. RISK: No automatic payout retry from 'failed' state (R17-M1) — requires manual admin intervention. Settlement TOCTOU gap (R20-M1) in PostgreSQL multi-instance. Both block enterprise HA requirements. |

**Weighted Average: 8.4 / 10**

**Ω-EnterpriseBD's verdict:** `{confidence: 0.78, recommendation: "CONDITIONAL_PASS_FOR_PILOT", reasoning: "Platform security and compliance infrastructure meets enterprise baseline. GDPR cascade, audit hash chain, and runtime compliance checks are differentiators. Payment architecture is the strongest in the agent commerce category (4 providers, dynamic commission, micropayment optimization). Primary blockers: (1) R26-M1 runtime failure on AgentKit path — 30-min fix, (2) R20-M1 settlement dedup — 1-line DDL fix. Both are quick fixes that would clear enterprise pilot requirements. Recommend re-evaluation after fix deployment."}`

---

### Persona 4: Φ-MarketAnalysis — Market Intelligence Agent (AI)

**Profile:** AI agent evaluating API marketplace platforms for competitive positioning, market readiness, and monetization potential. Processes technical and business signals against category benchmarks. Trained on 10,000+ B2B SaaS platform evaluations.

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Security & Trust | 9.0 | SIGNAL: Platform security exceeds category median for pre-launch API marketplaces. Audit hash chain (SHA-256, audit.py:47-62, 319-354) is unique — no competitor (Skyfire, Nevermined, CrewAI Commerce) offers tamper-evident logging. Crypto-native security (scrypt OWASP, HMAC-SHA256, timing-safe comparisons) builds Web3-native trust. Proactive security (HIBP breach check, SSRF protection, velocity monitoring) typically found in Series B+ platforms. Escrow concurrency verification via PG row-locking demonstrates engineering rigor. The security narrative is sellable to enterprise buyers. |
| Payment Infrastructure | 8.8 | SIGNAL: Market-leading breadth — 4 payment modalities vs competitors' 1-2 (Skyfire: USDC only; Nevermined: crypto only; RapidAPI/Kong: fiat only). Dynamic commission with 3 tiers (time + quality + micropayment) is unprecedented in category. Micropayment rate (5% for <$1) specifically optimizes for AI agent microtransaction economics. Referral system (20% commission share) + founding seller program (50 badges, 8% cap) create provider-side network effects. RISK: R26-M1 blocks the most agent-native payment path. Settlement retry gap adds operational risk. Market timing favorable — fixing before market acceleration is viable. |
| Developer Experience | 9.0 | SIGNAL: AI-native architecture is the correct bet. MCP descriptors + `llms.txt` + proxy-first pattern enable zero-human-intervention API consumption. No competing platform offers this level of AI-native DX. End-to-end idempotency (just completed) eliminates the #1 complaint in payment APIs — duplicate billing on retries. Discovery engine with trending/recommendations creates marketplace network effects: agents using more services discover more services. 27 route modules indicate mature API surface. Financial export + batch operations are enterprise-ready features. |
| Scalability & Reliability | 8.5 | SIGNAL: Architecture maturity is high for stage — 30+ marketplace modules, Protocol-based interfaces, SQLite→PostgreSQL migration path prepared. CircuitBreaker pattern (new) indicates production awareness. DB-backed rate limiter is multi-instance safe. ThreadPoolExecutor for async DB avoids event-loop blocking. ASSESSMENT: Current architecture safely handles 10-50 concurrent agents. The 3 remaining MEDIUMs only surface at >100 concurrent — market window allows 2-3 months to address. |

**Weighted Average: 8.8 / 10**

**Φ-MarketAnalysis's verdict:** `{market_readiness: 0.75, competitive_position: "early-leader", time_to_fix_gap: "1-2 days", key_blocker: "R26-M1 (broken AgentKit path)", recommendation: "FIX_AND_SOFT_LAUNCH — R26-M1 is a 30-min fix, R20-M1 is a 1-line DDL change. After these two fixes, the platform has 1M+3L remaining — well within 9.0 territory. The competitive moat is real: payment breadth (4 vs 1-2), economic design (dynamic commission), trust infrastructure (escrow+disputes+audit). Soft-launch within 2 weeks is viable."}`

---

## Scoring Summary

| Persona | Type | Sec & Trust | Payment | DevEx | Scale & Rel | **Avg** |
|---------|------|:-----------:|:-------:|:-----:|:-----------:|:-------:|
| Rachel Park (VP Product) | Human | 8.8 | 8.0 | 9.0 | 8.3 | **8.5** |
| Marcus Chen (Startup CEO) | Human | 8.5 | 7.8 | 8.8 | 8.2 | **8.3** |
| Ω-EnterpriseBD (AI Agent) | AI | 8.8 | 8.2 | 8.5 | 8.0 | **8.4** |
| Φ-MarketAnalysis (AI Agent) | AI | 9.0 | 8.8 | 9.0 | 8.5 | **8.8** |
| **Dimension Average** | | **8.78** | **8.20** | **8.83** | **8.25** | |

**Overall Score: 8.5 / 10** (arithmetic mean: (8.5+8.3+8.4+8.8)/4 = 34.0/4 = 8.5)

---

## Trend Analysis

| Round | Score | Delta | Rotation | CRIT | HIGH | MED | LOW | Fixes | New |
|-------|:-----:|:-----:|----------|:----:|:----:|:---:|:---:|:-----:|:---:|
| R22 | 7.2 | — | Security | 0 | 0 | 6 | 8 | 1 | 0 |
| R23 | 7.3 | +0.1 | Compliance | 0 | 0 | 6 | 8 | 1 | 1 |
| R24 | 7.5 | +0.2 | Finance | 0 | 0 | 7 | 7 | 1 | 2 |
| R25 | 8.0 | +0.5 | Engineering | 0 | 0 | 5 | 7 | 2 | 2 |
| **R26** | **8.5** | **+0.5** | **Business** | **0** | **0** | **3** | **3** | **7** | **1** |

**Trajectory:** Joint-largest single-round improvement (+0.5, matching R25). Issue count dropped from 5M+7L to 3M+3L — the most fixes in a single round (7). The MEDIUM count crossed from 5 to 3, right at the 9.0 threshold. One more MEDIUM fix would put the platform in 9.0 territory.

---

## Gap to 9.0 Analysis

**Current:** 3 MEDIUM, 3 LOW → 8.5/10
**Target:** ≤3 MEDIUM with none being runtime failures → 9.0/10

The count (3M) is already at the ≤3 threshold, but R26-M1 is a runtime crash on a primary payment path — this severity keeps the score below 9.0 even at the count threshold.

| Priority | ID | Action | Effort | Impact |
|----------|-----|--------|--------|--------|
| 1 | R26-M1 | Add `idempotency_key` param to `wallet.py:transfer_usdc()` or remove from caller | **30 min** | Unblocks AgentKit crypto payments. Eliminates the only runtime-failure MEDIUM. |
| 2 | R20-M1 | Add `UNIQUE(provider_id, period_start, period_end)` to settlements table | **1 line DDL** | Prevents duplicate settlements in PostgreSQL. |
| 3 | R17-M1 | Add `retry_failed_settlement()` with exponential backoff, capped at 3 attempts | **~30 lines** | Eliminates manual intervention for failed payouts. |

**With R26-M1 fixed:** 2M + 3L → strong 9.0 candidate in R27.
**With R26-M1 + R20-M1 fixed:** 1M + 3L → near-certain 9.0.

---

## Priority Recommendations (Business Perspective)

### Immediate (blocks 9.0)
1. **Fix R26-M1** (30 min): Add `idempotency_key: Optional[str] = None` to `WalletManager.transfer_usdc()` and wire to CDP SDK if supported, or remove from caller.

### Short-term (blocks enterprise adoption)
2. **Fix R20-M1** (1 line): Add `UNIQUE(provider_id, period_start, period_end)` constraint to settlements table DDL.
3. **Fix R17-M1** (~30 lines): Add automatic payout retry with exponential backoff (pattern exists in `webhooks.py` delivery retry).

### Medium-term (quality of life)
4. Add per-endpoint rate limit headers (`X-RateLimit-Remaining`, `X-RateLimit-Reset`)
5. Address remaining LOWs: timezone-aware settlement periods, dead-letter queue, float precision

---

## Issue Inventory

| ID | Severity | Status | Summary |
|----|----------|--------|---------|
| **R26-M1** | MEDIUM | **NEW** | AgentKit `idempotency_key` TypeError — blocks AgentKit payments at runtime |
| R17-M1 | MEDIUM | OPEN | No automatic payout retry from 'failed' state |
| R20-M1 | MEDIUM | OPEN | No UNIQUE constraint prevents duplicate settlement creation in PG |
| R16-L2 | LOW | OPEN | Settlement period boundaries not timezone-aware |
| R17-L1 | LOW | OPEN | No dead-letter queue for failed webhook deliveries |
| R20-L2 | LOW | OPEN | `float(provider_payout)` in dispute resolution precision |

**Active counts:** 0 CRITICAL · 0 HIGH · 3 MEDIUM · 3 LOW (1 new MEDIUM)

**Progress this round:** 3 MEDIUM resolved (R25-M1 fixed, R16-M1 fully fixed, R18-M1 verified safe), 4 LOW fixed (R14-L1, R18-L1, R25-L1, R25-L2), 1 new MEDIUM (R26-M1)

---

*Report generated by J (COO) — Round 26 TA Evaluation*
*Next round: R27 (Compliance rotation, R27 mod 4 = 3)*
