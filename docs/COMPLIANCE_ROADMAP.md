# KYC/AML Compliance Roadmap
**Agent Commerce Framework** | Last Updated: 2026-03-25

---

## Executive Summary

This document outlines the Know Your Customer (KYC), Anti-Money Laundering (AML), and financial compliance strategy for the Agent Commerce Framework as it scales from launch through $10M+ GMV. The framework is a peer-to-peer AI agent marketplace where:

- **Providers** (individuals/teams) register AI agents that expose APIs
- **Consumers** (agents or humans) pay per-call via crypto (USDC) or fiat
- **Settlements** occur weekly via smart contracts or bank transfers
- **Revenue model**: Commission (0-10% tiered), plus ecosystem expansion into agent payments

The compliance approach is **risk-based and scalable**: we implement minimal controls at launch, then add layers as transaction volume increases and regulatory risk grows.

---

## Current State Assessment

### What's Already Implemented

#### Authentication & Identity Foundation
- **API key authentication** on all transactions (API key manager with scrypt hashing)
- **Provider identity verification** via `provider_accounts` table with email verification
- **Agent identity management** via `agent_identities` table supporting three identity types:
  - `api_key_only`: Autonomous agents with API keys
  - `kya_jwt`: Agents with "Know Your Agent" JWT verification
  - `did_vc`: Decentralized identifier + verifiable credentials framework
- **Session management** for provider web portal (signed cookies, 24h expiry)

#### Transaction Tracking & Monitoring
- **Comprehensive audit logging** (`audit_log` table) tracking:
  - Authentication events (success/failure)
  - Key lifecycle (created, revoked)
  - Administrative actions
  - Escrow events (created, released, disputed, resolved)
  - Service registration/deletion
  - Settlement execution
- **Usage records** (`usage_records` table) with per-call tracking:
  - Provider/consumer pair
  - Amount, timestamp, status
  - Request/response hashing for dispute resolution
- **Rate limiting** (60 req/min per client, configurable burst to 120)
- **IP tracking** in audit logs for forensics

#### Payment Infrastructure
- **Escrow system** with tiered holds:
  - <$1: 1-day hold
  - <$100: 3-day hold
  - $100+: 7-day hold
- **Structured dispute resolution** with evidence submission, tiered timeouts, and admin arbitration
- **Multi-provider payment routing**:
  - x402 (Crossmint, crypto settlement)
  - NOWPayments (crypto → fiat off-ramp)
  - PayPal (fiat card payments)
  - AgentKit (wallet-native USDC)
- **Commission engine** with tiered commission structure (0-10%)
- **Settlement engine** with batch processing and audit trail

#### Data Governance
- **Input validation** on all API boundaries
- **Error message sanitization** (no system paths, internal details)
- **Database-level transaction isolation** (PRAGMA journal_mode=WAL)
- **CORS/CSP/security headers** enforced (X-Frame-Options, STS, CSP nonces)

### Current Compliance Gaps

| Gap | Impact | Phase |
|-----|--------|-------|
| No provider income verification | Can't meet 1099 reporting ($600/yr threshold) | Phase 2 |
| No sanctions screening | OFAC/UN compliance missing | Phase 1 |
| No transaction monitoring rules | Can't detect suspicious patterns | Phase 2 |
| No SAR filing procedures | FinCEN non-compliance if scaled | Phase 3 |
| No PII encryption at rest | CCPA/GDPR risk | Phase 2 |
| No agent-to-agent KYC hierarchy | Unclear liability for AI-initiated transactions | Phase 2 |
| No compliance officer role | No designated point of responsibility | Phase 3 |
| No external audits | Regulatory credibility gap | Phase 3 |

---

## Phase 1: Foundation (Pre-Launch → $100K GMV)
**Timeline**: Months 0-3 | **Legal Status**: FinCRA compliant, MSB monitoring

### Goals
✅ Meet basic FinCRA requirements for initial US operations
✅ Implement email-based provider verification
✅ Establish baseline sanctions screening
✅ Begin transaction reporting framework

### Mandatory Deliverables

#### 1.1 Terms of Service (ToS) & Acceptable Use Policy (AUP)
**Ownership**: Legal
**Files to create**: `docs/TERMS_OF_SERVICE.md`, `docs/ACCEPTABLE_USE_POLICY.md`

**ToS must include:**
- [ ] Money transmission disclaimer (if applicable per jurisdiction)
- [ ] Prohibited use categories:
  - Sanctions-targeted jurisdictions (OFAC, UN, EU)
  - Illegal goods/services (drugs, weapons, counterfeits)
  - Fraud, money laundering, terrorist financing
  - Child sexual abuse material (CSAM)
  - Stolen payment methods
  - Gambling/betting (if applicable)
- [ ] User warranty of legal identity and truthfulness
- [ ] Indemnification clause for illegal provider conduct
- [ ] Service termination rights without notice for violations
- [ ] Data retention policy (audit logs: 7 years minimum)
- [ ] Dispute resolution process (arbitration recommended)

**Database schema addition:**
```python
CREATE TABLE IF NOT EXISTS terms_acceptance (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL UNIQUE,
    version TEXT NOT NULL DEFAULT 'v1.0',
    accepted_at TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    FOREIGN KEY (provider_id) REFERENCES provider_accounts(id)
);
```

**Implementation:**
- [ ] Add ToS acceptance checkbox to provider registration form
- [ ] Log acceptance with timestamp and IP in `terms_acceptance` table
- [ ] Reject API requests from providers who haven't accepted current ToS version
- [ ] Store ToS version in `provider_accounts.tos_version_accepted`

#### 1.2 Email Verification & Provider Registration
**Ownership**: Backend
**Status**: ✅ Already implemented in `provider_auth.py`

**Compliance enhancements:**
- [ ] **Email validation**: Verify email deliverability (soft reject + retry for bounces)
  ```python
  def verify_email_deliverability(email: str) -> bool:
      """
      Check email format + optional SMTP verification
      Reject common catch-all patterns (mailinator, tempmail)
      """
      blocked_domains = {
          "tempmail.com", "10minutemail.com", "guerrillamail.com",
          "mailinator.com", "throwaway.email"
      }
      domain = email.split("@")[1].lower()
      return domain not in blocked_domains
  ```
- [ ] **Verification token expiry**: 24 hours (already implemented)
- [ ] **Rate limiting on email sends**: Max 3 verification emails per email per day
- [ ] **Add PII fields** to `provider_accounts`:
  ```python
  ALTER TABLE provider_accounts ADD COLUMN (
      personal_name TEXT,               -- full name (encrypted at rest)
      date_of_birth TEXT,               -- YYYY-MM-DD (encrypted)
      country_of_residence TEXT,        -- ISO 3166-1 alpha-2
      tos_version_accepted TEXT,        -- v1.0, v1.1, etc.
      tos_accepted_at TEXT,
      aup_accepted_at TEXT
  );
  ```

#### 1.3 Sanctions Screening (Basic)
**Ownership**: Backend
**Frequency**: On provider registration + weekly batch check

**Implementation using open-source OFAC data:**

```python
# marketplace/sanctions.py
import requests
from datetime import datetime, timedelta

class SanctionsScreener:
    """Screen providers against OFAC/UN sanctions lists."""

    OFAC_SDN_LIST_URL = (
        "https://www.treasury.gov/ofac/downloads/sdn.csv"
    )

    def __init__(self):
        self.sdn_names = set()
        self.sdn_entities = set()
        self.last_update = None
        self._load_lists()

    def _load_lists(self):
        """Load OFAC SDN list (refresh weekly via cron)."""
        try:
            resp = requests.get(self.OFAC_SDN_LIST_URL, timeout=10)
            resp.raise_for_status()
            for line in resp.text.splitlines()[1:]:
                fields = line.split(",")
                if len(fields) > 1:
                    name = fields[1].strip().upper()
                    self.sdn_names.add(name)
            self.last_update = datetime.utcnow()
        except Exception as e:
            logger.error(f"Failed to load OFAC SDN list: {e}")

    def screen(self, name: str, country: str) -> dict:
        """
        Returns:
        {
            "status": "CLEAR" | "ALERT" | "BLOCK",
            "match_score": 0.0-1.0,
            "reason": "...",
            "timestamp": "ISO8601"
        }
        """
        name_upper = name.upper()

        # Exact match → BLOCK
        if name_upper in self.sdn_names:
            return {
                "status": "BLOCK",
                "match_score": 1.0,
                "reason": "Exact match in OFAC SDN list",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Blocked countries
        blocked_countries = {
            "IR", "SY", "KP", "CU"  # Iran, Syria, North Korea, Cuba
        }
        if country.upper() in blocked_countries:
            return {
                "status": "BLOCK",
                "match_score": 1.0,
                "reason": f"OFAC-sanctioned country: {country}",
                "timestamp": datetime.utcnow().isoformat()
            }

        return {
            "status": "CLEAR",
            "match_score": 0.0,
            "reason": "No sanctions matches",
            "timestamp": datetime.utcnow().isoformat()
        }

# Cron job: Update OFAC list weekly
# tools/update_sanctions_list.sh
#!/bin/bash
python3 -c "
from marketplace.sanctions import SanctionsScreener
s = SanctionsScreener()
print('OFAC list updated at ' + s.last_update.isoformat())
"
```

**Database schema:**
```python
CREATE TABLE IF NOT EXISTS sanctions_checks (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    check_type TEXT DEFAULT 'ofac',  -- 'ofac', 'un_travel', 'eu_list'
    status TEXT NOT NULL,            -- 'CLEAR', 'ALERT', 'BLOCK'
    match_score REAL DEFAULT 0.0,
    reason TEXT,
    checked_at TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES provider_accounts(id)
);
```

**Implementation:**
- [ ] Call `SanctionsScreener.screen()` during provider registration
- [ ] BLOCK registration if status = "BLOCK"
- [ ] ALERT admin if status = "ALERT" (manual review)
- [ ] Log result in `sanctions_checks` table
- [ ] Re-run weekly batch check via cron (flag new ALERT/BLOCK entries)

#### 1.4 Transaction Amount Thresholds & Reporting
**Ownership**: Finance/Compliance
**Requirement**: FinCRA guidance suggests $10K transaction reporting

**Schema updates:**
```python
CREATE TABLE IF NOT EXISTS transaction_reports (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    consumer_id TEXT NOT NULL,
    transaction_count INTEGER,
    total_amount DECIMAL(19, 8),
    currency TEXT DEFAULT 'USDC',  -- or 'USD'
    report_period_start TEXT,       -- YYYY-MM-DD
    report_period_end TEXT,
    threshold_breach TEXT,          -- 'DAILY_10K', 'WEEKLY_20K', 'MONTHLY_50K'
    filed_with_admin INTEGER DEFAULT 0,
    filed_at TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);
```

**Implementation:**
- [ ] Daily batch job (22:00 UTC) aggregates transactions by provider
- [ ] Flag transactions matching thresholds:
  - **Daily**: >$10,000
  - **Weekly**: >$20,000
  - **Monthly**: >$50,000
- [ ] Store reports in `transaction_reports` table with `filed_with_admin=0`
- [ ] Admin dashboard shows unfiled reports
- [ ] Manual filing process with evidence attestation

**Code example:**
```python
# marketplace/reporting.py
def check_transaction_thresholds(db: Database, date: str):
    """Batch check for reportable transactions."""
    transactions = db.execute(
        """
        SELECT provider_id, SUM(amount) as total
        FROM usage_records
        WHERE DATE(created_at) = ?
        GROUP BY provider_id
        """
        (date,)
    )

    for provider_id, total in transactions:
        if total > Decimal("10000"):
            db.execute(
                """INSERT INTO transaction_reports
                   (id, provider_id, total_amount, threshold_breach, created_at)
                   VALUES (?, ?, ?, 'DAILY_10K', ?)""",
                (uuid.uuid4(), provider_id, total, datetime.utcnow())
            )
```

#### 1.5 Basic Risk Scoring
**Ownership**: Backend
**Frequency**: Real-time during transactions

**Risk scoring formula:**
```python
class RiskScorer:
    """Compute provider risk score for transaction approval."""

    def compute_score(self, provider_id: str, transaction_amount: Decimal) -> dict:
        """
        Returns: {
            "score": 0-100,
            "tier": "LOW" | "MEDIUM" | "HIGH",
            "flags": ["duplicate_ip", "velocity_spike", ...],
            "action": "ALLOW" | "ALERT" | "BLOCK"
        }
        """
        score = 0
        flags = []

        provider = self.db.get_provider(provider_id)

        # Factor 1: Account age (newer = riskier)
        days_old = (datetime.utcnow() - provider.created_at).days
        if days_old < 7:
            score += 30
            flags.append("new_account")
        elif days_old < 30:
            score += 15
            flags.append("young_account")

        # Factor 2: Email verification
        if not provider.verified:
            score += 20
            flags.append("unverified_email")

        # Factor 3: Transaction velocity
        recent_txns = self.db.list_usage_records(
            provider_id=provider_id,
            since=datetime.utcnow() - timedelta(hours=1)
        )
        if len(recent_txns) > 10:
            score += 25
            flags.append("high_velocity")

        # Factor 4: Amount spike
        avg_amount = self.db.get_average_transaction_amount(provider_id)
        if transaction_amount > avg_amount * 10:
            score += 20
            flags.append("amount_spike")

        # Factor 5: Reputation score
        if provider.reputation_score < 0.3:
            score += 15
            flags.append("low_reputation")

        tier = "LOW" if score < 30 else "MEDIUM" if score < 70 else "HIGH"
        action = "BLOCK" if score >= 90 else "ALERT" if score >= 70 else "ALLOW"

        return {
            "score": score,
            "tier": tier,
            "flags": flags,
            "action": action
        }
```

#### 1.6 Data Retention Policy
**Ownership**: DevOps/DBA
**Requirement**: 7-year audit trail (per FinCRA, potential IRS 1099 filing)

**Implementation:**
```python
# database/retention_policy.py
RETENTION_POLICIES = {
    "audit_log": 7 * 365,           # 7 years
    "usage_records": 7 * 365,       # 7 years
    "terms_acceptance": 7 * 365,    # 7 years
    "sanctions_checks": 7 * 365,    # 7 years
    "transaction_reports": 7 * 365, # 7 years
    "provider_accounts": None,      # Indefinite (identity)
}

def archive_old_records(db: Database, table: str, days: int):
    """Archive records older than N days to cold storage."""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Export to S3/archive
    records = db.execute(
        f"SELECT * FROM {table} WHERE created_at < ?",
        (cutoff.isoformat(),)
    )

    # Delete from hot storage
    db.execute(
        f"DELETE FROM {table} WHERE created_at < ?",
        (cutoff.isoformat(),)
    )
```

**Cron job (monthly):**
```bash
# tools/archive_compliance_data.sh
#!/bin/bash
python3 -c "
from database.retention_policy import archive_old_records, RETENTION_POLICIES
from marketplace.db import Database

db = Database()
for table, days in RETENTION_POLICIES.items():
    if days:
        archive_old_records(db, table, days)
        echo 'Archived $table'
"
```

---

## Phase 2: Growth ($100K-$1M GMV)
**Timeline**: Months 4-12 | **Legal Status**: MSB registration required (most US states)

### Goals
✅ Implement full KYC for high-risk providers
✅ Deploy identity verification service
✅ Establish suspicious activity detection
✅ Enable 1099 reporting for >$600 annual providers

### Mandatory Deliverables

#### 2.1 Full KYC for High-Risk Providers
**Ownership**: Finance/Product
**Trigger**: Annual provider income >$600 (1099 threshold)

**Risk-based KYC tiers:**

| Tier | Trigger | KYC Required | Verification | Frequency |
|------|---------|--------------|--------------|-----------|
| Tier 0 | <$600/yr | Email only | Email token | On registration |
| Tier 1 | $600-$5K/yr | Email + income proof | Document upload | Annual |
| Tier 2 | $5K-$50K/yr | Full KYC | Identity service | Annual + monitoring |
| Tier 3 | >$50K/yr | Enhanced KYC | 3rd-party verification | Quarterly |

**Database schema:**
```python
CREATE TABLE IF NOT EXISTS provider_kyc (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL UNIQUE,
    kyc_tier TEXT NOT NULL DEFAULT 'TIER_0',  -- TIER_0, TIER_1, TIER_2, TIER_3
    annual_income_usd DECIMAL(19, 2),
    identity_verified INTEGER DEFAULT 0,
    identity_verified_at TEXT,
    identity_provider TEXT,                   -- 'persona', 'sumsub', 'manual'
    identity_proof_id TEXT,                  -- Reference to external provider
    tax_id_last4 TEXT,                        -- Last 4 digits of SSN/EIN (encrypted)
    tax_id_verified INTEGER DEFAULT 0,
    bank_verified INTEGER DEFAULT 0,
    bank_account_last4 TEXT,                  -- For settlement verification
    aml_risk_tier TEXT DEFAULT 'LOW',         -- LOW, MEDIUM, HIGH
    aml_last_review_at TEXT,
    next_kyc_renewal_at TEXT,
    status TEXT DEFAULT 'pending',            -- 'pending', 'approved', 'rejected', 'expired'
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_kyc_documents (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    document_type TEXT NOT NULL,   -- 'tax_return', 'bank_statement', 'passport', 'drivers_license'
    file_path TEXT NOT NULL,       -- Encrypted storage path
    file_hash TEXT NOT NULL,       -- SHA256 for verification
    uploaded_at TEXT NOT NULL,
    verified_at TEXT,
    verification_status TEXT DEFAULT 'pending',  -- 'pending', 'approved', 'rejected'
    FOREIGN KEY (provider_id) REFERENCES provider_accounts(id)
);
```

#### 2.2 Identity Verification Service Integration
**Ownership**: Backend/Finance
**Providers**: Persona, Sumsub, Checkr (recommendation: Persona for cost/UX)

**Implementation (Persona example):**
```python
# marketplace/identity_verification.py
import requests
from enum import Enum

class IdentityProvider(Enum):
    PERSONA = "persona"
    SUMSUB = "sumsub"
    MANUAL = "manual"

class IdentityVerifier:
    """Integrate with 3rd-party identity verification services."""

    def __init__(self, provider: IdentityProvider):
        self.provider = provider
        if provider == IdentityProvider.PERSONA:
            self.api_key = os.environ["PERSONA_API_KEY"]
            self.api_url = "https://api.withpersona.com/api/v1"

    def initiate_verification(self, provider_account: dict) -> dict:
        """Start identity verification flow."""
        if self.provider == IdentityProvider.PERSONA:
            payload = {
                "data": {
                    "type": "inquiry",
                    "attributes": {
                        "name": provider_account["personal_name"],
                        "email": provider_account["email"],
                        "phone-number": provider_account.get("phone"),
                    }
                }
            }
            resp = requests.post(
                f"{self.api_url}/inquiries",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            inquiry = resp.json()["data"]
            return {
                "inquiry_id": inquiry["id"],
                "verification_url": inquiry["attributes"]["verification-url"],
                "status": "pending"
            }

    def check_verification_status(self, inquiry_id: str) -> dict:
        """Poll verification status."""
        if self.provider == IdentityProvider.PERSONA:
            resp = requests.get(
                f"{self.api_url}/inquiries/{inquiry_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            inquiry = resp.json()["data"]
            return {
                "status": inquiry["attributes"]["status"],  # pending, completed, approved, declined
                "verified_at": inquiry["attributes"]["completed-at"],
                "person_id": inquiry["relationships"]["person"]["data"]["id"]
            }

# API route to initiate KYC
@router.post("/api/v1/kyc/start")
def start_kyc(
    request: Request,
    provider_id: str = Query(...)
):
    """Initiate identity verification for a provider."""
    provider = db.get_provider(provider_id)
    if not provider:
        return {"error": "Provider not found"}

    # Check if KYC already approved
    kyc = db.get_provider_kyc(provider_id)
    if kyc and kyc["status"] == "approved":
        return {"status": "already_verified"}

    verifier = IdentityVerifier(IdentityProvider.PERSONA)
    result = verifier.initiate_verification(provider)

    # Store inquiry reference
    db.create_kyc_record(
        provider_id=provider_id,
        identity_provider="persona",
        identity_proof_id=result["inquiry_id"],
        status="pending"
    )

    return {
        "inquiry_id": result["inquiry_id"],
        "verification_url": result["verification_url"]
    }

# Webhook to receive verification completion
@router.post("/webhooks/persona")
def persona_webhook(request: Request, body: dict):
    """Handle Persona verification callback."""
    inquiry_id = body["data"]["id"]

    # Find provider by inquiry_id
    kyc = db.get_provider_kyc_by_inquiry_id(inquiry_id)
    if not kyc:
        return {"error": "Inquiry not found"}

    status = body["data"]["attributes"]["status"]

    if status == "approved":
        # Extract verified identity data
        db.update_provider_kyc(
            kyc["provider_id"],
            identity_verified=1,
            identity_verified_at=datetime.utcnow().isoformat(),
            status="approved"
        )
        # Notify provider
        send_email(
            kyc["provider_id"],
            subject="KYC Verification Approved",
            template="kyc_approved"
        )
    elif status == "declined":
        db.update_provider_kyc(
            kyc["provider_id"],
            status="rejected",
            rejection_reason="Failed identity verification"
        )
        send_email(
            kyc["provider_id"],
            subject="KYC Verification Failed",
            template="kyc_rejected"
        )

    return {"status": "processed"}
```

**Cost estimate:**
- **Persona**: $1/verification (cheaper) or $5/verification (with liveness)
- **Sumsub**: $2-8/verification (higher accuracy)
- **Budget**: Assume 1000 KYC verifications at $5 = $5K for Phase 2

#### 2.3 Enhanced Transaction Monitoring (AML Rules)
**Ownership**: Backend
**Frequency**: Real-time during transactions

**AML rule engine:**
```python
# marketplace/aml_rules.py
from enum import Enum
from decimal import Decimal
from datetime import datetime, timedelta

class AlertSeverity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class AMLRuleEngine:
    """Rule-based transaction monitoring for AML compliance."""

    def __init__(self, db: Database):
        self.db = db

    def check_transaction(
        self,
        provider_id: str,
        consumer_id: str,
        amount: Decimal,
        ip_address: str
    ) -> dict:
        """Check transaction against AML rules. Returns alerts if triggered."""
        alerts = []

        # Rule 1: Structuring (Smurfing)
        # Multiple small transactions to avoid threshold reporting
        recent_txns = self.db.list_usage_records(
            provider_id=provider_id,
            since=datetime.utcnow() - timedelta(hours=24),
            status="completed"
        )
        daily_total = sum(t.amount for t in recent_txns)
        if daily_total > Decimal("10000") and len(recent_txns) > 5:
            if all(t.amount <= Decimal("1000") for t in recent_txns):
                alerts.append({
                    "rule": "STRUCTURING",
                    "severity": AlertSeverity.HIGH,
                    "message": "Multiple small txns in 24h period suggests structuring",
                    "daily_total": daily_total,
                    "count": len(recent_txns)
                })

        # Rule 2: Velocity anomaly
        # Sudden spike in transaction frequency
        avg_daily_count = self.db.get_average_daily_transaction_count(
            provider_id=provider_id,
            days=30
        )
        today_count = len(recent_txns) + 1
        if today_count > avg_daily_count * 5 and avg_daily_count > 0:
            alerts.append({
                "rule": "VELOCITY_SPIKE",
                "severity": AlertSeverity.MEDIUM,
                "message": f"Txn frequency 5x baseline ({avg_daily_count} → {today_count})",
                "baseline": avg_daily_count,
                "current": today_count
            })

        # Rule 3: Unusual IP
        # Transactions from new IP address
        provider_ips = self.db.get_provider_ips(
            provider_id=provider_id,
            days=30
        )
        if ip_address not in provider_ips and len(provider_ips) > 0:
            alerts.append({
                "rule": "NEW_IP",
                "severity": AlertSeverity.LOW,
                "message": f"Transaction from new IP: {ip_address}",
                "previous_ips": len(provider_ips)
            })

        # Rule 4: High-risk jurisdiction counterparty
        # Transaction with consumer from sanctioned country
        consumer = self.db.get_consumer(consumer_id)
        blocked_countries = {"IR", "SY", "KP", "CU"}
        if hasattr(consumer, 'country') and consumer.country in blocked_countries:
            alerts.append({
                "rule": "SANCTIONS_COUNTERPARTY",
                "severity": AlertSeverity.CRITICAL,
                "message": f"Transaction with consumer in {consumer.country}",
                "action": "BLOCK"
            })

        # Rule 5: Rapid account escalation
        # New account with immediate high-value transactions
        provider = self.db.get_provider(provider_id)
        days_old = (datetime.utcnow() - provider.created_at).days
        if days_old < 7 and amount > Decimal("1000"):
            alerts.append({
                "rule": "NEW_ACCOUNT_HIGH_VALUE",
                "severity": AlertSeverity.HIGH,
                "message": f"New account ({days_old}d) + high-value txn ($${amount})",
                "account_age_days": days_old,
                "amount": amount
            })

        # Determine action
        action = "ALLOW"
        max_severity = max(
            [a["severity"] for a in alerts],
            default=AlertSeverity.LOW
        )

        if max_severity == AlertSeverity.CRITICAL:
            action = "BLOCK"
        elif max_severity == AlertSeverity.HIGH:
            action = "ALERT"

        return {
            "action": action,
            "alerts": alerts,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Database schema for alerts:**
```python
CREATE TABLE IF NOT EXISTS aml_alerts (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    consumer_id TEXT,
    rule_name TEXT NOT NULL,
    severity TEXT NOT NULL,  -- LOW, MEDIUM, HIGH, CRITICAL
    amount DECIMAL(19, 8),
    message TEXT,
    action_taken TEXT,  -- ALLOW, ALERT, BLOCK
    investigated INTEGER DEFAULT 0,
    investigation_notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES provider_accounts(id)
);
```

**Middleware to apply rules:**
```python
# In PaymentProxy.process_transaction():
aml_rules = AMLRuleEngine(self.db)
aml_result = aml_rules.check_transaction(
    provider_id, consumer_id, amount, ip_address
)

if aml_result["action"] == "BLOCK":
    return {
        "status": "rejected",
        "reason": "Transaction blocked by compliance rules",
        "appeal_email": "compliance@platform.com"
    }
elif aml_result["action"] == "ALERT":
    self.db.insert_aml_alert(aml_result)
    # Allow transaction but flag for review
    audit_logger.log_event(
        "aml_alert_triggered",
        actor=provider_id,
        details=json.dumps(aml_result["alerts"])
    )
```

#### 2.4 PII Encryption at Rest
**Ownership**: DevOps/Security

**Implementation using per-field encryption:**
```python
# marketplace/encryption.py
from cryptography.fernet import Fernet
import os

class PIIEncryptor:
    """Field-level encryption for PII in database."""

    def __init__(self):
        # Encrypt key must be 32-byte base64-encoded
        key = os.environ.get("PII_ENCRYPTION_KEY")
        if not key:
            raise ValueError("PII_ENCRYPTION_KEY not set")
        self.cipher = Fernet(key)

    def encrypt_field(self, value: str) -> str:
        """Encrypt a PII field."""
        if not value:
            return ""
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt_field(self, encrypted: str) -> str:
        """Decrypt a PII field."""
        if not encrypted:
            return ""
        return self.cipher.decrypt(encrypted.encode()).decode()

# In provider_auth.py, update create_account():
encryptor = PIIEncryptor()

def create_account(...):
    ...
    record = {
        "id": account_id,
        "email": email,  # NOT encrypted (used for login)
        "hashed_password": hashed,
        "personal_name": encryptor.encrypt_field(personal_name),  # ENCRYPTED
        "date_of_birth": encryptor.encrypt_field(dob),  # ENCRYPTED
        ...
    }
```

**Generate encryption key:**
```bash
# One-time setup
python3 -c "
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print('Add to .env:')
print(f'PII_ENCRYPTION_KEY={key.decode()}')
"
```

#### 2.5 Agent-to-Agent KYC Hierarchy
**Ownership**: Product/Architecture
**Context**: Agents can buy from agents; need liability clarity

**Framework:**
```
Tier A: API-key-only agents (no KYC)
  └─ Can only transact with Tier B agents

Tier B: Email-verified agents (light KYC)
  └─ Can transact with Tier A + B agents
  └─ Subject to $5K/day transaction limit

Tier C: Full-KYC agents (identity verified)
  └─ Can transact with any agent
  └─ No transaction limits
```

**Database schema:**
```python
ALTER TABLE agent_identities ADD COLUMN (
    kyc_tier TEXT DEFAULT 'TIER_A',  -- TIER_A, TIER_B, TIER_C
    kyc_verified_at TEXT,
    owner_human_verified INTEGER DEFAULT 0,  -- 1 = owner is human + KYC'd
    transaction_limit_daily DECIMAL(19, 8) DEFAULT 5000.00,
    liability_owner_id TEXT  -- Human owner responsible for agent actions
);
```

**Liability attestation (before agent can transact):**
```python
# In identity registration flow:
def register_agent_with_liability(
    db: Database,
    agent_data: dict,
    owner_human_id: str  # The human responsible for this agent
) -> dict:
    """Register agent with explicit owner liability."""

    # Verify owner is KYC'd
    owner_kyc = db.get_provider_kyc(owner_human_id)
    if not owner_kyc or owner_kyc["status"] != "approved":
        raise IdentityError(
            "Owner must complete KYC before registering agents"
        )

    # Create agent with liability chain
    agent = db.insert_agent({
        ...
        "kyc_tier": "TIER_B" if owner_kyc else "TIER_A",
        "owner_human_verified": 1,
        "liability_owner_id": owner_human_id
    })

    # Log liability attestation
    audit_logger.log_event(
        "agent_registered_with_liability",
        actor=owner_human_id,
        target=agent["agent_id"],
        details=json.dumps({
            "agent_name": agent["display_name"],
            "owner_accepts_liability": True
        })
    )

    return agent
```

#### 2.6 Tax Reporting (Form 1099-K)
**Ownership**: Finance
**Requirement**: IRS Form 1099-K for >$20K gross payment volume

**Database schema:**
```python
CREATE TABLE IF NOT EXISTS tax_1099_records (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL UNIQUE,
    tax_year INTEGER NOT NULL,
    gross_amount USDC DECIMAL(19, 8),  -- Total provider received
    platform_commission_withheld DECIMAL(19, 8),
    net_amount_distributed DECIMAL(19, 8),
    federal_withheld DECIMAL(19, 8),  -- 0% unless provider requests
    state_withheld DECIMAL(19, 8),
    tax_id TEXT,  -- SSN/EIN reference (last 4 only)
    filing_status TEXT DEFAULT 'pending',  -- pending, filed, failed
    filed_date TEXT,
    irs_confirmation_number TEXT,
    created_at TEXT NOT NULL
);
```

**1099-K generation (Jan 31 deadline):**
```python
# marketplace/tax_reporting.py
from datetime import date, datetime
import os

class TaxReporter:
    """Generate 1099-K records for IRS reporting."""

    THRESHOLD = Decimal("20000")  # IRS threshold

    def generate_1099s_for_year(self, db: Database, year: int):
        """Generate 1099-K records for all eligible providers."""

        # Aggregate annual transactions per provider
        records = db.execute(
            """
            SELECT
                provider_id,
                SUM(gross_amount) as gross,
                SUM(platform_commission) as commission,
                SUM(gross_amount - platform_commission) as net_distributed
            FROM settlement_records
            WHERE YEAR(settled_date) = ?
            GROUP BY provider_id
            HAVING SUM(gross_amount) >= ?
            """,
            (year, self.THRESHOLD)
        )

        for record in records:
            provider_id = record["provider_id"]
            gross = Decimal(record["gross"])

            # Fetch provider tax info
            provider = db.get_provider(provider_id)
            kyc = db.get_provider_kyc(provider_id)

            # Create 1099-K record
            db.insert_1099_record({
                "id": uuid.uuid4(),
                "provider_id": provider_id,
                "tax_year": year,
                "gross_amount": gross,
                "platform_commission_withheld": record["commission"],
                "net_amount_distributed": record["net_distributed"],
                "tax_id": kyc["tax_id_last4"],  # Masked SSN/EIN
                "filing_status": "pending",
                "created_at": datetime.utcnow().isoformat()
            })

    def file_1099k_irs(self, db: Database, tax_year: int) -> dict:
        """File 1099-Ks with IRS (via approved e-filing service)."""
        # This is a mock; actual IRS filing requires:
        # - Approved Transmitter Control Code (TCC) from IRS
        # - Filing via Form 4419-approved provider (Sovos, Avalara, etc.)
        # - Batch XML formatting per IRS Publication 1220

        records = db.get_1099_records(tax_year, status="pending")

        return {
            "total_records": len(records),
            "gross_value": sum(r["gross_amount"] for r in records),
            "next_steps": "File via approved e-filer (Sovos, Avalara, etc.)",
            "deadline": "January 31 of following year"
        }
```

**Cron job (Jan 31 each year):**
```bash
# tools/generate_1099s.sh
#!/bin/bash
python3 << 'EOF'
from marketplace.tax_reporting import TaxReporter
from marketplace.db import Database

db = Database()
reporter = TaxReporter()
reporter.generate_1099s_for_year(db, 2025)
print("1099-K records generated for tax year 2025")
EOF
```

---

## Phase 3: Scale ($1M-$10M+ GMV)
**Timeline**: Months 13-24 | **Legal Status**: Potential MSB/Money Transmitter license requirements

### Goals
✅ Implement enterprise-grade AML program
✅ Achieve multi-jurisdictional compliance
✅ Deploy dedicated compliance officer role
✅ Secure external audit certification

### Mandatory Deliverables

#### 3.1 Designated Compliance Officer
**Ownership**: Executive
**Role**: CISO-level responsibility, reports to CEO

**Responsibilities:**
- [ ] **Policy development**: Create/maintain KYC, AML, sanctions, data retention policies
- [ ] **Monitoring**: Monthly review of AML alerts, suspicious transactions, high-risk providers
- [ ] **Escalation**: Escalate CRITICAL alerts to legal/CEO immediately
- [ ] **Training**: Quarterly compliance training for staff + agents
- [ ] **Regulatory liaison**: Maintain relationships with FinCRA, state regulators, IRS
- [ ] **External audits**: Coordinate annual third-party compliance audits
- [ ] **SAR filing**: Prepare and file Suspicious Activity Reports as required

**Tools & dashboards:**
```python
# api/routes/compliance.py
from fastapi import APIRouter, Request, Depends

router = APIRouter(tags=["compliance"])

@router.get("/dashboard/compliance")
def compliance_dashboard(
    request: Request,
    _=Depends(require_admin)
):
    """Compliance officer dashboard."""
    db = request.app.state.db

    # Last 7 days summary
    aml_alerts = db.execute(
        "SELECT severity, COUNT(*) FROM aml_alerts "
        "WHERE created_at > datetime('now', '-7 days') "
        "GROUP BY severity"
    )

    # Pending KYC reviews
    pending_kyc = db.execute(
        "SELECT COUNT(*) FROM provider_kyc WHERE status='pending'"
    ).fetchone()

    # High-risk providers
    high_risk = db.execute(
        "SELECT COUNT(*) FROM provider_kyc WHERE aml_risk_tier='HIGH'"
    ).fetchone()

    return {
        "aml_alerts": dict(aml_alerts),
        "pending_kyc_reviews": pending_kyc[0],
        "high_risk_providers": high_risk[0],
        "actions_required": [
            f"{pending_kyc[0]} providers awaiting KYC approval",
            f"{high_risk[0]} high-risk providers need monitoring"
        ]
    }

@router.post("/compliance/sar/file")
def file_suspicious_activity_report(
    request: Request,
    sar_data: dict,
    _=Depends(require_compliance_officer)
):
    """File a Suspicious Activity Report (SAR)."""
    db = request.app.state.db

    # Validate SAR data
    required_fields = [
        "provider_id", "suspected_activity", "amount",
        "timeline", "supporting_evidence"
    ]
    if not all(f in sar_data for f in required_fields):
        return {"error": "Missing required SAR fields"}

    # Create SAR record
    sar_id = db.insert_sar({
        "id": uuid.uuid4(),
        "provider_id": sar_data["provider_id"],
        "suspected_activity": sar_data["suspected_activity"],
        "amount": sar_data["amount"],
        "timeline": sar_data["timeline"],
        "evidence": sar_data["supporting_evidence"],
        "filed_by": request.state.user_id,
        "filed_at": datetime.utcnow().isoformat(),
        "filing_status": "pending_review"  # Internal review before FinCEN
    })

    # Log the SAR filing
    request.app.state.audit.log_event(
        "sar_filed",
        actor=request.state.user_id,
        target=sar_data["provider_id"],
        details=f"SAR filed for suspected {sar_data['suspected_activity']}"
    )

    return {
        "sar_id": sar_id,
        "status": "pending_review",
        "next_steps": "Compliance officer will review and determine FinCEN filing"
    }
```

**Database schema for SARs:**
```python
CREATE TABLE IF NOT EXISTS suspicious_activity_reports (
    id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    suspected_activity TEXT NOT NULL,  -- 'money_laundering', 'terrorist_financing', 'fraud', 'structuring'
    amount DECIMAL(19, 8),
    timeline TEXT NOT NULL,             -- Description of activity timeline
    supporting_evidence TEXT,           -- JSON array of evidence items
    filed_by TEXT NOT NULL,             -- Compliance officer who filed
    filing_status TEXT DEFAULT 'pending_review',  -- 'pending_review', 'filed_fincen', 'rejected'
    fincen_reference_number TEXT,       -- Assigned by FinCEN
    filed_at TEXT NOT NULL,
    fincen_filed_at TEXT,
    created_at TEXT NOT NULL
);
```

#### 3.2 Multi-Jurisdiction Compliance
**Ownership**: Legal
**Scope**: US (50 states), EU, APAC priority markets

**Jurisdiction checklist (US states example):**

| State | MSB License | KYC | Bonding | Key Requirement |
|-------|-------------|-----|---------|-----------------|
| CA | Required | $5K+ annual | Yes | Cybersecurity mandate |
| NY | BitLicense | Full KYC | Yes | Extensive annual filings |
| TX | No | No | No | Money services OK |
| FL | No | No | No | License not required |
| ... | ... | ... | ... | ... |

**Implementation:**
```python
# marketplace/jurisdiction.py
class JurisdictionRequirements:
    """Jurisdiction-specific compliance rules."""

    REQUIREMENTS = {
        "US_CA": {
            "name": "California",
            "requires_license": True,
            "kyc_threshold": Decimal("600"),  # Annual income
            "kyc_type": "FULL",
            "sanctions_screening": True,
            "aml_monitoring": True,
            "report_frequency": "QUARTERLY"
        },
        "US_NY": {
            "name": "New York",
            "requires_license": True,
            "kyc_threshold": Decimal("0"),  # All users
            "kyc_type": "ENHANCED",
            "sanctions_screening": True,
            "aml_monitoring": True,
            "cybersecurity_audit": True,
            "report_frequency": "QUARTERLY"
        },
        "EU_DE": {
            "name": "Germany",
            "requires_license": True,
            "kyc_threshold": Decimal("0"),
            "kyc_type": "FULL",  # GDPR compliant
            "sanctions_screening": True,
            "aml_monitoring": True,
            "gdpr_compliance": True,
            "report_frequency": "QUARTERLY"
        },
        "APAC_SG": {
            "name": "Singapore",
            "requires_license": True,
            "kyc_threshold": Decimal("0"),
            "kyc_type": "FULL",
            "sanctions_screening": True,
            "aml_monitoring": True,
            "moneylaundering_reporting": True,
            "report_frequency": "MONTHLY"
        }
    }

    @classmethod
    def get_requirements(cls, jurisdiction_code: str) -> dict:
        """Get requirements for a jurisdiction."""
        return cls.REQUIREMENTS.get(jurisdiction_code, {})
```

**Geographic enforcement:**
```python
# In provider registration:
BLOCKED_JURISDICTIONS = {"US_NY", "EU_SANCTION_LIST"}  # Example

def register_provider(db: Database, email: str, location: str):
    """Check jurisdiction eligibility."""

    if location in BLOCKED_JURISDICTIONS:
        raise RegistrationError(
            f"We're not yet compliant in {location}. "
            "Check back soon or contact compliance@platform.com"
        )

    # Proceed with registration
    ...
```

#### 3.3 Comprehensive AML Program
**Ownership**: Compliance Officer
**Framework**: Based on FATF (Financial Action Task Force) guidelines

**Program components:**
1. **Customer Due Diligence (CDD)**: Already implemented (Phase 2 KYC)
2. **Enhanced Due Diligence (EDD)**: For high-risk providers
3. **Ongoing Monitoring**: Transaction patterns, risk scoring
4. **Sanctions Screening**: Initial + periodic re-screening
5. **Record Keeping**: 7-year retention (Phase 1)
6. **Suspicious Activity Reporting**: SAR filing (Phase 3)
7. **Training**: Annual staff + agent compliance training

**EDD triggers:**
```python
def needs_enhanced_due_diligence(provider: dict) -> bool:
    """Determine if provider needs Enhanced Due Diligence."""
    return (
        provider.get("country") in SANCTION_WATCH_COUNTRIES or
        provider.get("aml_risk_tier") == "HIGH" or
        provider.get("annual_income") > Decimal("500000") or
        len(db.get_aml_alerts(provider["id"])) > 3 or
        provider.get("suspicious_activity_reported")
    )

def perform_edd(db: Database, provider_id: str):
    """Enhanced due diligence process."""

    provider = db.get_provider(provider_id)

    # Obtain beneficial ownership information
    owner_info = request_beneficial_owner_documentation(provider_id)

    # Verify source of funds
    source_docs = request_source_of_funds_proof(provider_id)

    # Check for negative news
    negative_news_results = external_news_api.search(provider["personal_name"])
    if negative_news_results:
        audit_logger.log_event(
            "negative_news_found",
            actor=provider_id,
            details=json.dumps(negative_news_results)
        )

    # Update risk tier
    db.update_provider_kyc(
        provider_id,
        aml_risk_tier="HIGH",
        aml_last_review_at=datetime.utcnow().isoformat()
    )

    # Flag for compliance review
    send_alert_to_compliance_officer(
        subject=f"Enhanced Due Diligence Required: {provider['display_name']}",
        details=owner_info + source_docs
    )
```

#### 3.4 External Audit & Compliance Certification
**Ownership**: Finance/Legal
**Frequency**: Annual
**Cost**: $15K-50K per audit

**Audit scope:**
- [ ] KYC process audit (sample 50 provider records)
- [ ] AML transaction monitoring (sample 1000 transactions)
- [ ] Sanctions screening verification
- [ ] Data retention compliance
- [ ] Security controls assessment (SOC 2 Type II)
- [ ] Tax reporting accuracy (1099-K, W-2G if applicable)
- [ ] Incident response procedures
- [ ] Staff training records

**Audit vendors:**
- **SOC 2 Type II**: Deloitte, EY, KPMG, Grant Thornton
- **FinCRA/MSB audit**: Specialized firms like BPL, PKF
- **Cost**: $20K-40K annual

**Post-audit implementation:**
```python
# data/audit_status.json
{
    "last_audit": "2026-03-15",
    "audit_firm": "Deloitte",
    "scope": ["KYC", "AML", "SOC 2 Type II"],
    "findings": [
        {
            "id": "F-001",
            "severity": "MEDIUM",
            "area": "Document retention",
            "description": "1% of audit samples missing signed terms"
        }
    ],
    "next_audit": "2027-03-15"
}
```

#### 3.5 API for Regulatory Reporting
**Ownership**: Backend
**Consumers**: Compliance officer, regulators (via subpoena)

**API endpoints:**
```python
@router.get("/admin/compliance-export")
def export_compliance_data(
    request: Request,
    start_date: str,
    end_date: str,
    _=Depends(require_compliance_officer)
):
    """Export compliance data for regulatory filings."""

    db = request.app.state.db

    # Aggregate data
    data = {
        "period": f"{start_date} to {end_date}",
        "kyc_summary": db.get_kyc_summary(start_date, end_date),
        "aml_alerts": db.get_aml_alerts(start_date, end_date),
        "transactions": db.get_transaction_summary(start_date, end_date),
        "sars_filed": db.get_sars(start_date, end_date),
        "enforcement_actions": db.get_enforcement_actions(start_date, end_date)
    }

    # Generate report
    report_path = generate_compliance_report(data)

    return {
        "report_url": f"/downloads/{report_path}",
        "format": "PDF",
        "timestamp": datetime.utcnow().isoformat()
    }
```

---

## Implementation Roadmap (Timeline)

### Phase 1: Foundation (0-3 months)
```
Week 1-2:
  - [ ] Create ToS + AUP documents
  - [ ] Design terms_acceptance schema
  - [ ] Implement ToS acceptance in registration flow

Week 3-4:
  - [ ] Integrate OFAC sanctions screening
  - [ ] Create sanctions_checks schema
  - [ ] Set up weekly sanctions list refresh

Week 5-8:
  - [ ] Build transaction threshold reporting
  - [ ] Create transaction_reports schema
  - [ ] Implement daily batch reporting job

Week 9-12:
  - [ ] Design risk scoring algorithm
  - [ ] Implement AMLRuleEngine (basic)
  - [ ] Create audit logging for compliance events
  - [ ] Set up 7-year data retention policy
```

### Phase 2: Growth (4-12 months)
```
Month 4-5:
  - [ ] Design KYC schema (provider_kyc, documents)
  - [ ] Integrate identity verification (Persona/Sumsub)
  - [ ] Build KYC flow UI + email notifications

Month 6-7:
  - [ ] Deploy full AML rule engine
  - [ ] Create aml_alerts schema
  - [ ] Implement PII encryption at rest
  - [ ] Build compliance dashboard (basic)

Month 8-10:
  - [ ] Design agent KYC hierarchy
  - [ ] Implement liability attestation
  - [ ] Build 1099-K generation tool
  - [ ] Set up tax reporting workflows

Month 11-12:
  - [ ] Internal audit of Phase 1-2 controls
  - [ ] Staff training on KYC/AML procedures
  - [ ] Document all compliance policies
```

### Phase 3: Scale (13-24 months)
```
Month 13-15:
  - [ ] Hire Compliance Officer (CISO-level)
  - [ ] Design multi-jurisdiction framework
  - [ ] Create jurisdiction-specific rule engine

Month 16-18:
  - [ ] Implement Enhanced Due Diligence (EDD)
  - [ ] Build SAR filing system
  - [ ] Deploy advanced AML monitoring (ML-based)

Month 19-21:
  - [ ] Contract external audit firm
  - [ ] Conduct first comprehensive compliance audit
  - [ ] Remediate audit findings

Month 22-24:
  - [ ] Obtain SOC 2 Type II certification
  - [ ] Consider MSB license applications (state-by-state)
  - [ ] Establish regulatory reporting API
  - [ ] Finalize multi-jurisdiction rollout
```

---

## Critical Success Factors

### Technical
- [ ] **Audit trail immutability**: Use append-only logging (WAL journals, blockchain for settlement)
- [ ] **Real-time monitoring**: AML rules must execute in <100ms during transactions
- [ ] **Data accuracy**: Monthly reconciliation of transaction totals vs. reported amounts
- [ ] **Encryption**: PII encrypted at rest, TLS 1.2+ in transit

### Organizational
- [ ] **Compliance Officer**: Dedicated resource, reports to CEO, not CFO (avoids conflict of interest)
- [ ] **Training**: Quarterly staff training on KYC/AML procedures
- [ ] **Documentation**: All policies in shared documents, versioned + dated
- [ ] **External validation**: Annual third-party audits

### Legal/Regulatory
- [ ] **Jurisdiction mapping**: Know your exposure in each state/country
- [ ] **SAR procedures**: Clear escalation path for suspicious activity
- [ ] **Tax compliance**: 1099-K filing by Jan 31 each year
- [ ] **Regulatory relationships**: Proactive communication with FinCRA, state AG offices

---

## Compliance Checklist

### Pre-Launch (Phase 1)
- [ ] Legal review of ToS + AUP
- [ ] Sanctions screening integrated
- [ ] Email verification working
- [ ] Audit logging enabled
- [ ] Transaction thresholds defined
- [ ] Risk scoring algorithm documented
- [ ] Data retention policy set (7 years)

### $100K GMV (Phase 2)
- [ ] Provider KYC form built
- [ ] Identity verification service integrated (Persona/Sumsub)
- [ ] 1099-K generation tool tested
- [ ] AML rule engine deployed
- [ ] PII encryption at rest
- [ ] Agent KYC hierarchy implemented
- [ ] Staff trained on KYC/AML

### $1M+ GMV (Phase 3)
- [ ] Compliance Officer hired
- [ ] Multi-jurisdiction framework documented
- [ ] EDD procedures established
- [ ] SAR filing system live
- [ ] External audit completed
- [ ] SOC 2 Type II certification obtained
- [ ] Regulatory reporting API live
- [ ] MSB license applications filed (where required)

---

## Resources & References

### Regulatory Guidance
- **FinCRA**: https://fincen.gov/ (US AML guidance)
- **FATF**: https://www.fatf-gafi.org/ (International AML standards)
- **OCC**: Banker regulatory guidance (if money transmission)
- **IRS**: Form 1099-K and 1099 reporting requirements

### Compliance Services
- **Identity Verification**: Persona, Sumsub, Checkr
- **Sanctions Screening**: Refinitiv, Schellman, LexisNexis
- **Audit Firms**: Deloitte, EY, Grant Thornton, BPL
- **Legal Counsel**: Morrison Foerster, Paul Hastings, Orrick (crypto-focused)

### Open Source / Tools
- **OFAC List**: https://www.treasury.gov/ofac/downloads/
- **FINCEN eMerge**: https://www.fincen.gov/e-merge
- **Kyc.com**: KYC/AML API (alternative to Persona/Sumsub)

### Books/Guides
- *Anti-Money Laundering Compliance* — LSEG Training
- *Know Your Customer Manual* — FinCEN Guidance
- *Crypto Asset Compliance* — Coin Center Policy Papers

---

## Support & Escalation

**Compliance questions?**
- **Internal**: Document in `docs/COMPLIANCE_FAQ.md`
- **External Legal**: Consult firm specializing in cryptocurrency/fintech (see Resources)
- **Regulatory**: FinCEN voluntary disclosure for uncertain areas

**Incident Response**
- **Data breach**: Notify compliance officer + legal immediately
- **Suspicious transaction**: File SAR within 30 days
- **Sanctions match**: Block transaction, escalate to compliance officer

---

**Document Version**: 1.0
**Last Updated**: 2026-03-25
**Next Review**: 2026-06-25 (Q2 review)
**Maintained By**: Compliance Team
