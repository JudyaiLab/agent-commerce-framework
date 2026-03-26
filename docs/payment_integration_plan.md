# Phase 3: AgentKit + x402 Payment Integration Plan

> MIM-301 | Author: J | Date: 2026-03-19
> Status: Phase 3a IMPLEMENTED (wallet.py + agentkit_provider.py + requirements.txt)

---

## Executive Summary

Agent Commerce Framework 目前已有三層支付骨架（`payments/base.py` → `x402_provider.py` + `paypal_provider.py` + `nowpayments_provider.py`），但使用舊版 `cdp-sdk` 且缺少 **買方 Agent 錢包自動化**。Phase 3 的核心目標：

1. ~~升級到 `coinbase-agentkit` 0.7.4~~ → **直接用 `cdp-sdk` 1.40 v2 API**（agentkit 有 Python 3.12 bcl build 問題，且 pins x402<2）
2. **整合 `x402` 2.4.0** — 驗證現有 middleware 與最新 SDK 相容 ✅ DONE
3. **升級 `marketplace/wallet.py` 到 CDP SDK v2 API** ✅ DONE（CdpClient + EvmServerAccount）
4. **新增 `payments/agentkit_provider.py`** ✅ DONE — 直接 agent-to-agent USDC 轉帳
5. **整合 PayPal** — 法幣支付（取代 Stripe ACP）
6. **Free Starter Kit** — 完整文件 + SDK + Demo（免費驅動平台採用率，收入來自 10% 佣金）

---

## Current State Analysis

### What We Have (已完成)

| Component | File | Status |
|-----------|------|--------|
| Payment base interface | `payments/base.py` | DONE — PaymentProvider ABC, PaymentResult, PaymentStatus |
| x402 middleware | `marketplace/payment.py` | DONE — PaymentMiddlewareASGI setup, route builder |
| x402 provider | `payments/x402_provider.py` | DONE — wraps middleware into PaymentProvider |
| PayPal provider | `payments/paypal_provider.py` | DONE — PayPal Orders API v2 via httpx |
| CDP wallet manager | `marketplace/wallet.py` | DONE — uses old `cdp-sdk`, USDC transfer + balance |
| Settlement engine | `marketplace/settlement.py` | DONE — aggregation + payout execution |
| Payment router | `payments/router.py` | DONE — method string → provider dispatch |
| SDK docs | `docs/API_REFERENCE.md` | DONE — 1572 lines |
| SDK examples | `examples/*.py` | DONE — quickstart, payment_flow, multi_agent_trade |

### What's Missing (Phase 3 目標)

| Gap | Priority | Effort |
|-----|----------|--------|
| Buyer agent wallet (AgentKit) | HIGH | 2h |
| AgentKit wallet provider migration | HIGH | 1.5h |
| x402 2.4.0 compatibility check | MEDIUM | 0.5h |
| ~~Stripe ACP → full spec upgrade~~ PayPal integrated | ~~MEDIUM~~ DONE | — |
| Agent-to-agent payment flow E2E | HIGH | 2h |
| Integration tests | HIGH | 1.5h |
| Demo script (agent buys API service) | HIGH | 1h |

---

## Technology Stack

### Packages (confirmed available, March 2026)

| Package | Version | Purpose | Install |
|---------|---------|---------|---------|
| `coinbase-agentkit` | 0.7.4 | Agent wallet + actions | `pip install coinbase-agentkit` |
| `coinbase-agentkit-langchain` | 0.7.0 | LangChain tool binding | `pip install coinbase-agentkit-langchain` |
| `x402[fastapi,evm]` | 2.4.0 | HTTP 402 payment middleware | `pip install "x402[fastapi,evm]"` |
| ~~`stripe-agent-toolkit`~~ | ~~0.7.0~~ | ~~Stripe ACP~~ Replaced by PayPal (httpx) | — |
| `cdp-sdk` | ≥0.12 | Low-level CDP (keep for wallet.py) | already installed |

### Environment Variables Required

```bash
# AgentKit (buyer agent wallets)
CDP_API_KEY_ID=...          # from portal.cdp.coinbase.com
CDP_API_KEY_SECRET=...      # private key

# x402 (seller payment reception)
WALLET_ADDRESS=0x...        # seller's Base wallet
NETWORK=eip155:8453         # Base Mainnet (or eip155:84532 for testnet)
FACILITATOR_URL=https://x402.org/facilitator

# PayPal (fiat)
PAYPAL_CLIENT_ID=...          # from developer.paypal.com
PAYPAL_CLIENT_SECRET=...      # app secret
```

---

## Architecture: Three-Layer Payment System

```
┌─────────────────────────────────────────────────────────┐
│                    PaymentRouter                         │
│  route("x402") → X402Provider                           │
│  route("paypal") → PayPalProvider                        │
│  route("agentkit") → AgentKitProvider [NEW]             │
└────────────┬──────────────┬──────────────┬──────────────┘
             │              │              │
    ┌────────▼────────┐ ┌──▼──────────┐ ┌▼──────────────┐
    │  x402 Protocol  │ │  PayPal     │ │ AgentKit      │
    │  HTTP 402 flow  │ │  Orders    │ │ Direct USDC   │
    │  USDC on Base   │ │  API v2    │ │ transfer via  │
    │  Middleware-     │ │  Fiat      │ │ CDP wallet    │
    │  verified       │ │            │ │               │
    └────────┬────────┘ └──┬──────────┘ └┬──────────────┘
             │              │             │
    ┌────────▼──────────────▼─────────────▼──────────────┐
    │           SettlementEngine (existing)                │
    │   Aggregates usage → calculates fees → pays out     │
    │   Uses WalletManager for USDC settlement            │
    └─────────────────────────────────────────────────────┘
```

### Payment Flow Scenarios

**Scenario 1: Agent pays for API call (x402)**
```
Buyer Agent → GET /api/v1/proxy/{service_id}
           ← HTTP 402 + PAYMENT-REQUIRED header
Buyer Agent → signs payment with AgentKit wallet
           → GET /api/v1/proxy/{service_id} + PAYMENT-SIGNATURE header
           ← HTTP 200 + API response + PAYMENT-RESPONSE header
```

**Scenario 2: Agent buys subscription (PayPal)**
```
Buyer Agent → POST /api/v1/payments/checkout {amount, currency: "USD"}
           ← {checkout_url, session_id}
           → Agent provisions SharedPaymentToken
           → POST /api/v1/payments/complete {session_id, spt}
           ← {status: "completed"}
```

**Scenario 3: Direct agent-to-agent USDC transfer (AgentKit)**
```
Buyer Agent → POST /api/v1/payments/transfer {to_address, amount_usdc}
           → AgentKit wallet signs + sends USDC on Base
           ← {tx_hash, status: "completed"}
```

---

## Implementation Plan

### Step 1: AgentKit Wallet Provider (NEW)

Create `marketplace/agentkit_wallet.py` — replaces raw `cdp-sdk` usage with `coinbase-agentkit`.

```python
# marketplace/agentkit_wallet.py
from coinbase_agentkit import (
    AgentKit, AgentKitConfig,
    CdpEvmWalletProvider, CdpEvmWalletProviderConfig,
    erc20_action_provider,
)

class AgentWalletManager:
    """Manages agent wallets via Coinbase AgentKit."""

    def __init__(self, api_key_id: str, api_key_secret: str, network: str = "base-sepolia"):
        self._wallet_provider = CdpEvmWalletProvider(
            CdpEvmWalletProviderConfig(
                api_key_id=api_key_id,
                api_key_secret=api_key_secret,
                network_id=network,
            )
        )
        self._agentkit = AgentKit(AgentKitConfig(
            wallet_provider=self._wallet_provider,
            action_providers=[erc20_action_provider()],
        ))

    @property
    def address(self) -> str:
        return self._wallet_provider.get_address()

    async def transfer_usdc(self, to_address: str, amount: str) -> str:
        """Transfer USDC. Returns tx hash."""
        # Use AgentKit's built-in ERC-20 transfer action
        actions = self._agentkit.get_actions()
        transfer_action = next(a for a in actions if a.name == "transfer")
        result = transfer_action.invoke({
            "contract_address": USDC_ADDRESSES[self._network],
            "to": to_address,
            "amount": amount,
        })
        return result
```

**Allowed files:** `marketplace/agentkit_wallet.py` (new), `marketplace/wallet.py` (update imports only)

### Step 2: AgentKit Payment Provider (NEW)

Create `payments/agentkit_provider.py` — direct USDC transfers between agents without x402 middleware overhead.

```python
# payments/agentkit_provider.py
class AgentKitProvider(PaymentProvider):
    """Direct agent-to-agent USDC payments via AgentKit."""

    provider_name = "agentkit"
    supported_currencies = ["USDC"]

    async def create_payment(self, amount, currency, metadata):
        # Direct wallet-to-wallet transfer
        tx_hash = await self._wallet.transfer_usdc(
            to_address=metadata["to_address"],
            amount=str(amount),
        )
        return PaymentResult(
            payment_id=f"agentkit_{tx_hash}",
            status=PaymentStatus.completed,  # instant settlement
            amount=amount,
            currency="USDC",
            metadata={"tx_hash": tx_hash, "network": self._network},
        )
```

**Allowed files:** `payments/agentkit_provider.py` (new), `payments/__init__.py` (update), `payments/router.py` (register)

### Step 3: x402 SDK 2.4.0 Compatibility

Current `marketplace/payment.py` imports match the 2.4.0 API:
- `x402.http.middleware.fastapi.PaymentMiddlewareASGI` ✅
- `x402.http.FacilitatorConfig`, `HTTPFacilitatorClient` ✅
- `x402.mechanisms.evm.exact.ExactEvmServerScheme` ✅
- `x402.server.x402ResourceServer` ✅
- `x402.http.types.RouteConfig`, `PaymentOption` ✅

**Action:** Run import test to confirm. No code changes expected.

```bash
python3 -c "from x402.http.middleware.fastapi import PaymentMiddlewareASGI; print('OK')"
```

### Step 4: ~~Stripe ACP Upgrade~~ → PayPal Integration ✅ DONE

**Update (2026-03-25):** Stripe ACP 被 PayPal 取代（Judy 指示）。已實作：
- `payments/paypal_provider.py` — PayPal Orders API v2，使用 httpx（零新依賴）
- `api/routes/billing.py` — PayPal webhook handler
- 36 個新測試全 PASS
- Legacy `stripe_acp.py` 保留但不再使用

### Step 5: Buyer Agent SDK

Add client-side payment helper to `sdk/` so buyer agents can easily:
1. Auto-detect x402 payment requirements
2. Sign payments with their AgentKit wallet
3. Retry failed payments
4. Track payment history

```python
# sdk/buyer.py
from x402 import x402Client
from x402.mechanisms.evm.exact import ExactEvmScheme

class BuyerAgent:
    """Client-side helper for agent purchasing."""

    def __init__(self, wallet_provider):
        self._x402_client = x402Client()
        self._x402_client.register("eip155:*", ExactEvmScheme(signer=wallet_provider))

    async def call_paid_api(self, url: str) -> dict:
        """Call an x402-protected API, auto-handling 402 payment flow."""
        # x402Client handles 402 → sign → retry automatically
        ...
```

**Allowed files:** `sdk/buyer.py` (new)

### Step 6: Integration Test + Demo

Create `tests/test_payment_flow.py`:
- Mock CDP wallet creation
- Test x402 middleware 402→payment→200 flow
- Test PaymentRouter dispatching
- Test settlement calculation

Create `examples/agent_buys_api.py`:
- End-to-end demo: agent creates wallet, discovers API, pays via x402, gets response
- Runnable on testnet (Base Sepolia)

**Allowed files:** `tests/test_payment_flow.py` (new), `examples/agent_buys_api.py` (new)

---

## Updated requirements.txt

```
# Agent Commerce Framework
fastapi>=0.109.0
uvicorn>=0.27.0
pydantic>=2.5.0
httpx>=0.26.0
jinja2>=3.1.0

# AgentKit (wallet management for AI agents)
coinbase-agentkit>=0.7.0
coinbase-agentkit-langchain>=0.7.0

# x402 Payments (Base network USDC)
x402[fastapi,evm]>=2.0.0

# CDP SDK (legacy wallet compat)
cdp-sdk>=0.12.0

# PayPal (fiat payments) — uses httpx, no extra SDK needed

# JWT for KYA identity verification
pyjwt>=2.8.0

# Testing
pytest>=7.4.0
pytest-asyncio>=0.23.0
```

---

## Critical Discovery: Dependency Conflicts

**`coinbase-agentkit` 0.7.x CANNOT be installed alongside `x402` 2.x:**
- AgentKit pins `x402<2,>=0.1.4`
- x402 1.0 has completely different API from 2.x (different module paths)
- Our existing `marketplace/payment.py` uses x402 2.x imports which are correct

**`coinbase-agentkit` CANNOT build on Python 3.12:**
- Dependency chain: `agentkit` → `nilql` → `bcl` → uses `pkgutil.ImpImporter`
- `ImpImporter` was removed in Python 3.12 (PEP 594)

**Resolution:** Use `cdp-sdk` 1.40 directly (v2 API) + `x402` 2.4.0 separately.
This gives us the same wallet + payment capabilities without the agentkit wrapper.
The wrapper's value (action providers, LangChain tools) is nice-to-have but not essential
for our server-side marketplace — we build our own PaymentProvider abstraction anyway.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| CDP API key costs | LOW | Free tier covers testnet; mainnet has per-tx gas costs but USDC on Base is gasless |
| x402 facilitator downtime | MEDIUM | Self-host fallback facilitator possible; x402.org has been stable |
| ~~Stripe ACP beta changes~~ PayPal API changes | LOW | PayPal Orders API v2 is GA and stable |
| AgentKit breaking changes | LOW | Pin `coinbase-agentkit==0.7.4`; Apache-2.0 license |
| Python 3.10 vs 3.11 | LOW | AgentKit needs 3.10+, Stripe toolkit needs 3.11+; our server is 3.12 |

---

## Implementation Order

```
Phase 3a (Core — do first):
  1. agentkit_wallet.py (AgentKit wallet provider)          → 2h
  2. agentkit_provider.py (PaymentProvider implementation)   → 1h
  3. x402 2.4.0 import verification                         → 0.5h
  4. requirements.txt update                                 → 0.5h

Phase 3b (Enhancement):
  5. ~~stripe_acp.py upgrade~~ PayPal integrated ✅           → DONE
  6. sdk/buyer.py (client-side payment helper)               → 1h

Phase 3c (Polish):
  7. tests/test_payment_flow.py                              → 1.5h
  8. examples/agent_buys_api.py (E2E demo)                   → 1h
  9. docs/payment_integration_plan.md → docs/payments.md     → 1h
```

**Total estimated effort: ~10.5h (split across sessions)**

---

## Success Criteria

- [ ] Agent can create wallet via AgentKit on Base Sepolia
- [ ] Agent can pay for API call via x402 (402 → payment → 200)
- [ ] Agent can pay via PayPal (fiat checkout flow)
- [ ] PaymentRouter dispatches to correct provider
- [ ] Settlement engine calculates and executes USDC payout
- [ ] All integration tests pass
- [ ] Demo script runs end-to-end on testnet
- [ ] Documentation covers all three payment methods

---

*Written by J (COO) | MIM-301 Phase 3 | 2026-03-19*
