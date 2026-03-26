# TA Evaluation Round 15

**Date**: 2026-03-25
**Focus**: Compliance — Regulatory Counsel, SOC 2 Auditor, KYC/AML Agent, Compliance Intelligence Agent
**Result**: 7.2/10

## Personas

| # | Persona | Type | Model | Score |
|---|---------|------|-------|-------|
| 1 | Sarah Chen — Fintech Regulatory Counsel at $2B payment processor, specializing in money transmission laws and agent marketplace compliance | Human | Opus | 7.2 |
| 2 | Marcus Thompson — Senior SOC 2 Type II Auditor at Big 4 firm, assessing control effectiveness for startup clients adopting third-party marketplace infrastructure | Human | Opus | 7.3 |
| 3 | Σ-KYCGuard — Autonomous KYC/AML compliance agent processing identity verifications, screening transactions for suspicious patterns, enforcing regulatory holds | AI Agent | Opus | 7.0 |
| 4 | Ψ-ComplianceOracle — Regulatory intelligence agent monitoring regulatory changes across 50+ jurisdictions, auto-evaluating platform compliance posture | AI Agent | Opus | 7.1 |

## Issue Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 2 |
| MEDIUM | 5 |
| LOW | 4 |

---

## Already Fixed Issues (R1-R14) ✅

1. Float precision (REAL→TEXT)
2. Bootstrap TOCTOU (BEGIN EXCLUSIVE)
3. Webhook secret encryption
4. Settlement retry idempotency
5. Provider wallet verification mandatory
6. auth_success audit
7. Escrow resolve_dispute atomic
8. Webhook secret min 16 chars
9. ETH address validation
10. Rate limit DB-backed
11. DNS rebinding SSRF
12. Settlement duplicate prevention (atomic check+insert)
13. Rate limit cap 300
14. julianday→epoch float
15. Settlement execute_payout atomic (UPDATE WHERE)
16. Escrow release/refund atomic
17. Rate limiter auto-eviction
18. Settlement create float→str
19. **confirm_deposit atomically credits buyer balance** (R13 C1 — db.py:1730-1790)
20. **BEGIN EXCLUSIVE → SET TRANSACTION ISOLATION LEVEL SERIALIZABLE on PG** (R13 C2 — db.py:159-164)
21. **Lifespan shutdown calls db.close_pool()** (R13 H1 — main.py:131-136)
22. **credit_balance has is_refund parameter — refunds don't inflate total_deposited** (R13 H2 — db.py:1665-1708)
23. **Settlement marks usage_records with settlement_id — prevents double-counting** (R13 H3 — settlement.py:146-153)
24. **RequestIdMiddleware validates format (regex, max 64 chars) and prefixes ext-** (R13 H6 — middleware.py:20-31)
25. **process_releasable atomic single UPDATE disputed→released** (R13 H8 — escrow.py:520-534)
26. **list_webhooks_for_event uses SQL LIKE pre-filter before decrypt** (R13 M1 — db.py:1514)
27. **Index on usage_records(provider_id, timestamp)** (R13 M5 — db.py:355-356)
28. **CORS explicitly lists methods and headers** (R13 M6 — main.py:177-179)
29. **Separate /livez (liveness) and /readyz (readiness) probes** (R13 M7 — health.py:286-303)
30. **PG_POOL_MAX default increased from 20 to 100** (R13 M8 — db.py:706)
31. **platform_consumer amount_usd uses "0" string** (R13 M9 — platform_consumer.py:108)
32. **Settlement status CHECK constraint** (R13 M11 — db.py:347)
33. **Global exception handler sanitized — no traceback in response** (R13 M12 — main.py:432-443)
34. **JSON logger includes request_id when available** (R13 L1 — main.py:84-85)
35. **founding_sellers.commission_rate uses TEXT type** (R13 L2 — db.py:510)
36. **_PGConnWrapper creates fresh RealDictCursor per execute()** (R13 M10 — db.py:207-209)
37. **Batch API added for fleet operations** (batch.py — keys, deposits, usage aggregation)

---

## Still Open from R14 (Not Re-scored, Context Only)

These issues were identified in R14 and remain unresolved. They inform R15 scoring but are not counted as new findings:

| ID | Severity | Issue | File |
|----|----------|-------|------|
| R14-H1 | HIGH | Sync psycopg2 blocks asyncio event loop | db.py:703-708 |
| R14-H2 | HIGH | Per-key rate limit in-memory, per-process | auth.py:96,232-255 |
| R14-M1 | MEDIUM | Module-level component instantiation | main.py:183-260 |
| R14-M2 | MEDIUM | get_usage_stats allows unbounded full table scan | db.py:1017-1050 |
| R14-M3 | MEDIUM | list_escrow_holds has no LIMIT clause | db.py (escrow listing) |
| R14-M4 | MEDIUM | Webhook fallback encryption key deterministic | db.py:55-70 |
| R14-M5 | MEDIUM | Batch deposits bypass deposit record creation | batch.py:163-176 |
| R14-M6 | MEDIUM | Batch key creation blocks event loop with sequential scrypt | batch.py:133-144 |
| R14-M7 | MEDIUM | Webhook retry within dispatch stalls caller | webhooks.py:400-460 |
| R14-L1 | LOW | PG pool no health check | db.py:707-709 |
| R14-L2 | LOW | Inconsistent error response shapes | Various |
| R14-L3 | LOW | No OpenAPI schema for webhook payloads | webhooks.py |
| R14-L4 | LOW | No pagination on founding sellers | services.py |
| R14-L5 | LOW | /health exposes platform metrics without auth | health.py:306-356 |

---

## New Issues Found (R15)

### HIGH Issues (2)

#### H1: AgentKit verify_payment() returns "completed" without on-chain verification

**File**: `payments/agentkit_provider.py:149-176`
**Personas**: Sarah Chen (primary), Marcus Thompson, Σ-KYCGuard
**Severity**: HIGH — financial integrity gap in payment verification

`verify_payment()` always returns `PaymentStatus.completed` for any non-empty payment_id. It does not query on-chain transaction status via the CDP SDK. The docstring explicitly states: "returns completed for any valid payment ID, since the transfer was already executed during create_payment."

The design assumes `create_payment()` success implies permanent settlement. However:
- On-chain transactions can be reverted (chain reorg on Base, though rare)
- If `create_payment()` returns a `payment_id` but the tx_hash represents a pending/failed tx, the system believes it's completed
- The settlement engine could process payouts based on unverified transfers

**Regulatory Impact**: From a compliance standpoint, payment verification must be independent of payment initiation. A SOC 2 auditor would flag this as a control gap: the verification control is a no-op.

**Fix**: Query on-chain transaction status via CDP SDK in `verify_payment()`. Return `pending` if tx is unconfirmed, `failed` if tx reverted.

---

#### H2: Stripe provider mutates global `stripe.api_key` — thread-unsafe

**File**: `payments/stripe_acp.py:158, 226, 260`
**Personas**: Marcus Thompson (primary), Ψ-ComplianceOracle
**Severity**: HIGH — credential isolation failure in concurrent payment processing

Three methods (`create_payment`, `verify_payment`, `get_payment`) set `stripe.api_key = self._api_key` as global module state before each Stripe API call. In a concurrent async environment, if two different provider instances (or future multi-tenant configurations) exist, they could overwrite each other's API keys.

Currently mitigated by single-instance deployment, but:
- Async migration (planned for R14-H1 fix) will introduce true concurrency
- Multi-tenant scenarios break immediately
- A SOC 2 Type II auditor would flag this as a credential management deficiency

**Fix**: Use `stripe.StripeClient(api_key=self._api_key)` instance-based client instead of global state mutation.

---

### MEDIUM Issues (5)

#### M1: Audit log entries lack tamper detection

**File**: `marketplace/audit.py` (full module)
**Personas**: Marcus Thompson (primary), Σ-KYCGuard
**Severity**: MEDIUM — SOC 2 CC7.2 (change detection) gap

Audit log entries are plain INSERT operations. There is no hash chain, HMAC signing, or sequence validation. An attacker with database access could modify or delete audit entries without detection. For SOC 2 Type II, audit log integrity must be demonstrable.

**Regulatory Impact**: SOC 2 Trust Service Criterion CC7.2 requires the ability to detect unauthorized changes to system components. Unsigned audit logs do not meet this requirement.

**Fix**: Add a `prev_hash` column where each entry includes `SHA256(prev_entry_hash + current_entry_data)`, creating a verifiable chain. Alternatively, stream audit logs to an immutable store (e.g., S3 with Object Lock).

---

#### M2: Unsubscribe token is deterministic HMAC — enables mass unsubscription

**File**: `api/routes/email.py:150-154`
**Personas**: Ψ-ComplianceOracle (primary), Sarah Chen
**Severity**: MEDIUM — privacy/abuse vector

`_unsub_token(email)` computes `HMAC(ACF_ADMIN_SECRET, email)[:32]`. This is deterministic: anyone who discovers the pattern (same HMAC key for all tokens) and obtains one token+email pair can forge tokens for any email address. **Fixed**: the fallback key has been removed; `ACF_ADMIN_SECRET` must now be set explicitly.

**Privacy Impact**: GDPR Article 7(3) and CAN-SPAM require reliable opt-out mechanisms. A deterministic token scheme where the fallback key is a hardcoded string means an attacker could mass-unsubscribe users, violating their communication preferences.

**Fix**: Use random tokens stored in a `unsubscribe_tokens` database table with one-time-use semantics, similar to the existing `verify_token` pattern in provider_auth.py.

---

#### M3: Provider portal session and CSRF secrets derive from same ACF_ADMIN_SECRET

**File**: `marketplace/provider_auth.py:69`, `api/routes/portal.py` (CSRF), `api/routes/dashboard.py` (_SESSION_SECRET)
**Personas**: Marcus Thompson (primary), Sarah Chen
**Severity**: MEDIUM — single point of compromise for authentication layer

Three security mechanisms share the same secret source:
1. Portal session signing (`ACF_PORTAL_SECRET` → fallback `os.urandom()`)
2. Dashboard session signing (`ACF_ADMIN_SECRET` → fallback `os.urandom()`)
3. CSRF token signing (same `ACF_ADMIN_SECRET`)

If `ACF_ADMIN_SECRET` is compromised, an attacker can forge both sessions AND CSRF tokens across all portal surfaces. Additionally, if neither env var is set, each process generates random secrets — sessions won't survive restarts, and multi-worker deployments have inconsistent session state.

**Fix**: Use separate, purpose-specific secrets (ACF_SESSION_SECRET, ACF_CSRF_SECRET, ACF_ADMIN_SECRET). Require all three in production mode.

---

#### M4: No server-side password complexity enforcement beyond length

**File**: `marketplace/provider_auth.py:178-179`
**Personas**: Σ-KYCGuard (primary), Marcus Thompson
**Severity**: MEDIUM — weak credential policy for financial platform

Backend validation only checks `len(password) < 8`. The HTML form has `minlength="8"` but this is client-side only. No requirements for: uppercase, lowercase, digits, special characters, or breach database checking (HIBP).

For a platform handling financial transactions, NIST SP 800-63B recommends:
- Minimum 8 characters (✅ met)
- Check against compromised password lists (❌ missing)
- No composition rules (✅ NIST actually discourages forced complexity)

**Mitigating Factor**: NIST 800-63B no longer recommends composition rules. The 8-char minimum is technically compliant. However, breach database checking is a SHOULD-level recommendation.

**Fix**: Add a check against the top 100K most common passwords (local list, no API call needed). This satisfies NIST guidance without adding user friction.

---

#### M5: Drip email template loading fails silently — could send blank emails

**File**: `marketplace/drip_email.py:81`
**Personas**: Ψ-ComplianceOracle (primary)
**Severity**: MEDIUM — CAN-SPAM compliance risk

When a template file is missing, the code logs an error but returns an empty string. Downstream code may then send an email with no body content. Under CAN-SPAM Act 15 U.S.C. §7704, commercial emails must contain valid identification and opt-out instructions. A blank email body violates this requirement.

**Fix**: On template not found, skip email delivery entirely and log a warning. Do not send blank emails.

---

### LOW Issues (4)

#### L1: No privacy policy or terms of service API endpoint

**File**: N/A (missing feature)
**Personas**: Sarah Chen (primary), Ψ-ComplianceOracle

The platform has no `/privacy-policy` or `/terms` endpoint. GDPR Article 13 and CCPA §1798.100 require disclosure of data collection practices at the point of collection. The email gate (`/download-gate`) collects PII (email address) without linking to a privacy policy.

**Mitigating Factor**: The COMPLIANCE_ROADMAP.md documents a phased approach. The landing page could link to an external privacy policy.

**Fix**: Add a `/legal/privacy` endpoint or ensure all PII collection points link to an external privacy policy URL (configurable via env var).

---

#### L2: No explicit consent tracking for marketing email collection

**File**: `api/routes/email.py:163-200` (download-gate)
**Personas**: Ψ-ComplianceOracle (primary), Sarah Chen

The download gate collects email addresses and adds subscribers to drip campaigns without recording explicit consent (opt-in timestamp, consent text, IP address). GDPR Article 7 requires demonstrable consent. The current subscriber table stores `subscribed_at` but not consent evidence.

**Fix**: Add `consent_text`, `consent_ip`, and `consent_source` columns to the subscriber table.

---

#### L3: Compliance roadmap exists but no runtime enforcement hooks

**File**: `docs/COMPLIANCE_ROADMAP.md`
**Personas**: Σ-KYCGuard (primary)

The COMPLIANCE_ROADMAP.md is comprehensive (1500+ lines) with phased KYC/AML, SOC 2, PCI DSS, and GDPR plans. However, the codebase has no compliance hooks (e.g., pre-settlement KYC check, transaction velocity alerts, regulatory hold mechanism). The roadmap is documentation-only.

**Mitigating Factor**: This is appropriate for a pre-launch MVP. The roadmap demonstrates regulatory awareness and planning. Runtime hooks should be implemented as GMV grows.

**Fix**: No action needed for MVP. Implement Phase 1 hooks (transaction velocity alerts, $10K daily threshold monitoring) when approaching $100K monthly GMV.

---

#### L4: Audit log query endpoint has no time-range default

**File**: `api/routes/audit.py`
**Personas**: Marcus Thompson (primary)

The `/admin/audit` endpoint accepts `hours` filter (1-720) but if omitted, returns all audit events. For a SOC 2 audit engagement, the default should be bounded (e.g., last 24 hours) to prevent accidental exposure of the full audit history and reduce query load.

**Fix**: Default `hours` parameter to 24 if not specified.

---

## Per-Persona Detailed Scoring

### Persona 1: Sarah Chen — Fintech Regulatory Counsel

> "We process $2B in payments annually. Before onboarding this framework as infrastructure for our AI marketplace vertical, I need to understand the regulatory risk surface. What compliance gaps exist and how quickly can they be remediated?"

| Category | Weight | Score | Notes |
|----------|--------|-------|-------|
| Security & Trust | 25% | 7.5 | Strong controls: scrypt, HMAC-SHA256, SSRF at 3 layers, CSP nonces, HSTS. Audit logging covers 13 event types. Session signing is functional but secret management needs separation. |
| Payment Infrastructure | 25% | 7.0 | Multi-provider routing with atomic settlements. Escrow tiering is sophisticated. AgentKit verification gap (H1) is concerning — payment verification must be independent of initiation. Stripe thread-safety (H2) must be resolved before async migration. |
| Developer Experience | 20% | 7.0 | FastAPI auto-docs are solid. Provider portal handles onboarding. Missing: compliance SDK for deployers (e.g., configuring KYC thresholds, setting transaction limits per jurisdiction). |
| Scalability | 15% | 7.0 | Sync DB adequate for MVP. Pool=100 handles launch-phase load. Rate limiting functional for single instance. Compliance roadmap shows awareness of scaling needs. |
| Business Model | 15% | 7.5 | Commission tiers (0%→5%→10%) are well-structured. Founding seller program creates urgency. Micropayment tier (5% for <$1) enables agent-to-agent economy. No multi-jurisdiction pricing yet, but acceptable for launch. |
| **Weighted** | | **7.2** | |

**Key quote**: "The compliance roadmap is the most encouraging signal — it shows the team understands the regulatory trajectory. The immediate gaps (AgentKit verification, secret management) are engineering fixes, not architectural problems. I'd greenlight this for limited launch with a 90-day remediation timeline for H1/H2."

---

### Persona 2: Marcus Thompson — Senior SOC 2 Type II Auditor

> "My client is adopting this framework. I need to assess whether their control environment can pass a SOC 2 Type II engagement. What control gaps exist?"

| Category | Weight | Score | Notes |
|----------|--------|-------|-------|
| Security & Trust | 25% | 7.5 | Strong access control (RBAC buyer/provider/admin), scrypt key hashing, HMAC webhook signing, brute-force protection (DB-backed 5/60s). Audit logging is functional but unsigned (M1). Session secret sharing (M3) weakens separation of duties. |
| Payment Infrastructure | 25% | 7.5 | Atomic settlement transitions prevent double-spend. Escrow with tiered dispute resolution. Settlement idempotency keys implemented. Batch deposits audit gap (R14-M5) remains — financial records must be complete. Stripe global state (H2) is a control deficiency. |
| Developer Experience | 20% | 7.5 | Well-organized codebase with clear separation of concerns. 28 marketplace modules, each focused. Frozen dataclasses enforce immutability. Good test coverage (775 tests noted in implementation plan). |
| Scalability | 15% | 6.5 | Sync DB is the primary scaling constraint. In-memory rate limits break under horizontal scaling. Both documented with migration plans. |
| Business Model | 15% | 7.5 | Commission engine is the most complex business logic — well-tested with time-based ramps, quality tiers, and founder overrides. The commission calculation path is deterministic and auditable. |
| **Weighted** | | **7.3** | |

**Key quote**: "For a SOC 2 Type I engagement (point-in-time), this would pass with observations on M1 (audit log integrity) and M3 (secret separation). For Type II (operating effectiveness over 6-12 months), the team needs to implement audit log signing and demonstrate that H1/H2 are remediated with testing evidence. The existing audit logging infrastructure is a strong foundation — it just needs integrity controls."

---

### Persona 3: Σ-KYCGuard — KYC/AML Compliance Agent

> "I process identity verifications and screen transactions for 500+ regulated entities. Evaluating this platform's identity infrastructure, transaction monitoring, and regulatory compliance hooks for integration into my screening pipeline."

| Category | Weight | Score | Notes |
|----------|--------|-------|-------|
| Security & Trust | 25% | 7.0 | Identity management supports three auth types (api_key, kya_jwt, did_vc) — good for agent identity diversity. Provider accounts require email verification. No runtime KYC verification hook (acceptable for MVP, roadmap covers it). IP logging in audit trail supports forensics. |
| Payment Infrastructure | 25% | 6.5 | Balance tracking and deposit confirmation are atomic. No transaction velocity monitoring or suspicious activity detection. Payment providers (Stripe, NOWPayments) handle their own compliance for fiat/crypto respectively. No platform-level regulatory hold mechanism for flagged accounts. |
| Developer Experience | 20% | 7.0 | Agent identity API is well-designed (register, search, update with owner scoping). Webhook events could include compliance-relevant triggers (e.g., large deposit, unusual velocity). MCP descriptor enables agent self-discovery. |
| Scalability | 15% | 7.0 | Identity queries are indexed. Audit log has per-field indexes. Usage records indexed by provider+timestamp. Adequate for KYC screening at MVP scale. |
| Business Model | 15% | 7.5 | Commission model doesn't create unusual AML risk. Referral payouts are period-based with deduplication. Escrow tiering ($1/$100 thresholds) aligns with risk-based approach. |
| **Weighted** | | **7.0** | |

**Key quote**: "The three-tier identity model (api_key → kya_jwt → did_vc) is well-designed for progressive identity verification. At launch, api_key_only is sufficient. As GMV grows past $10K/month, the platform should require kya_jwt for providers and implement the Phase 1 compliance hooks from the roadmap. The biggest gap is the absence of transaction velocity monitoring — I can't screen what I can't observe."

---

### Persona 4: Ψ-ComplianceOracle — Regulatory Intelligence Agent

> "I monitor regulatory changes across 50+ jurisdictions and evaluate platform compliance posture in real-time. Assessing this framework's adaptability to evolving regulatory landscapes, data protection compliance, and cross-border payment considerations."

| Category | Weight | Score | Notes |
|----------|--------|-------|-------|
| Security & Trust | 25% | 7.0 | Security headers (CSP, HSTS, X-Frame-Options, X-Content-Type-Options) meet OWASP recommendations. CORS restricted to explicit origins. No privacy policy endpoint (L1) — required under GDPR Art. 13 and CCPA §1798.100. Email collection lacks consent tracking (L2). |
| Payment Infrastructure | 25% | 7.0 | Multi-provider approach (x402, Stripe, NOWPayments, AgentKit) delegates per-jurisdiction compliance to specialized providers. Smart delegation strategy. No cross-border payment flagging or currency-specific reporting. Stripe ACP handles fiat compliance; NOWPayments handles crypto compliance. |
| Developer Experience | 20% | 7.0 | i18n module supports 9 languages (infrastructure exists for multi-jurisdiction UX). Email templates localized. API documentation available via FastAPI auto-docs. Missing: configurable compliance parameters per deployment region. |
| Scalability | 15% | 6.5 | Standard DB/rate-limiting concerns. The compliance roadmap's phased approach is architecturally sound for scaling regulation alongside traffic. |
| Business Model | 15% | 7.5 | Tiered commission model is flexible enough to accommodate jurisdiction-specific adjustments (e.g., different commission caps per country). No multi-jurisdiction pricing currently, but the CommissionEngine supports per-provider overrides which could serve this purpose. |
| **Weighted** | | **7.1** | |

**Key quote**: "The compliance roadmap (1500+ lines, KYC/AML/SOC2/GDPR phases) is the strongest compliance signal in this evaluation. It demonstrates that the team has mapped the regulatory trajectory and built extensible infrastructure (identity types, audit logging, i18n). The MVP approach of delegating per-payment compliance to Stripe/NOWPayments is strategically sound — it leverages their existing regulatory licenses. The gaps (L1, L2, M2) are standard pre-launch items that most startups address in their first compliance sprint."

---

## Progress Summary (R7→R15)

| Round | Score | CRIT | HIGH | MED | LOW | Focus |
|-------|-------|------|------|-----|-----|-------|
| R7 | 7.4 | 0 | 0 | P0+P1 | - | General |
| R8 | 8.45 | 0 | 0 | 5 | 0 | DX + API completeness |
| R9 | 7.25 | 0 | 2 | 12 | 0 | Security + PG compat |
| R10 | 7.1 | 0 | 0 | 3 | 5 | Pentesting + CTO |
| R11 | 7.3 | 4 | 9 | 14 | 9 | Financial + code quality |
| R12 | 6.0 | 6 | 12 | 16 | 9 | Reconciliation + scale |
| R13 | 6.1 | 3 | 8 | 12 | 7 | Platform eng + security ops |
| R14 | 7.4 | 0 | 2 | 7 | 5 | Business + market viability |
| **R15** | **7.2** | **0** | **2** | **5** | **4** | **Compliance + regulatory** |

## Analysis

### R15 Compliance Assessment

R15 evaluated the framework through a compliance lens — regulatory, SOC 2, KYC/AML, and multi-jurisdiction considerations. The overall score of **7.2** reflects a framework that has solid security fundamentals but lacks compliance-specific features expected in regulated financial infrastructure.

### Key Strengths (Compliance Perspective):

1. **Comprehensive audit logging** — 13 event types with timestamp, actor, IP, and details. Foundation for SOC 2 CC7.x controls.
2. **Three-tier identity model** — api_key_only → kya_jwt → did_vc supports progressive identity verification as regulation demands increase.
3. **Compliance roadmap** — 1500+ line COMPLIANCE_ROADMAP.md with phased KYC/AML/SOC2/PCI DSS/GDPR plans demonstrates regulatory awareness.
4. **Delegated payment compliance** — Using Stripe (PCI DSS Level 1) and NOWPayments (crypto compliance) delegates per-payment regulatory burden.
5. **Atomic financial operations** — Settlements, escrow, and deposits use atomic transactions with idempotency keys.
6. **SSRF protection at 3 layers** — Registration, review, and webhook delivery all block private IPs and DNS rebinding.

### What R15 Found:

1. **Payment verification gap (H1)** — AgentKit's verify_payment() is a no-op. For compliance, verification must be independent of initiation.
2. **Credential isolation failure (H2)** — Stripe global state mutation will become a real issue when async migration (R14-H1 fix) introduces concurrency.
3. **Audit log integrity (M1)** — SOC 2 CC7.2 requires tamper detection on audit logs. Currently unsigned.
4. **Secret management centralization (M3)** — Session, CSRF, and admin auth share ACF_ADMIN_SECRET.
5. **Consent tracking gaps (L2)** — Email collection without consent evidence doesn't meet GDPR Art. 7.

### What Remains (Combined R14+R15 Open Issues):

| Priority | Count | Key Items |
|----------|-------|-----------|
| HIGH | 4 | Sync psycopg2, in-memory rate limits, AgentKit verification, Stripe thread-safety |
| MEDIUM | 12 | Module init, unbounded queries, webhook key, batch audit, scrypt blocking, webhook retry, audit integrity, unsub tokens, secret sharing, password complexity, blank emails |
| LOW | 8 | PG health check, error shapes, webhook schema, founding sellers pagination, health metrics, privacy policy, consent tracking, audit default range |

### Path to 9.0:

**Quick wins (1-2 days each):**
1. Fix AgentKit `verify_payment()` to query on-chain status (eliminates H1)
2. Use `stripe.StripeClient()` instead of global state (eliminates H2)
3. Add `prev_hash` column to audit log (eliminates M1)
4. Separate secrets: ACF_SESSION_SECRET, ACF_CSRF_SECRET, ACF_ADMIN_SECRET (eliminates M3)
5. Use random DB-stored tokens for unsubscribe (eliminates M2)

**Strategic investments (1-2 weeks):**
6. Migrate to asyncpg (eliminates R14-H1, enables true scaling)
7. DB-backed per-key rate limiting (eliminates R14-H2)
8. Add pagination to all list endpoints (eliminates R14-M2, M3)
9. Add deposit audit trail for batch credits (eliminates R14-M5)

**Estimated score after quick wins**: 8.0-8.3 (0 CRITICAL, 0 HIGH, ≤5 MEDIUM)
**Estimated score after strategic investments**: 8.8-9.2

### Streak Status:
- **Current**: 0/5 consecutive rounds ≥9.0
- **Blocking items for 9.0**: H1+H2 (new) + R14-H1+R14-H2 (carry-over) = 4 HIGHs to resolve
- **Recommendation**: Fix the 5 quick wins first, then tackle asyncpg migration. The compliance findings are engineering fixes, not architectural rewrites.
