# TA Evaluation Round 8

**Date**: 2026-03-25
**Models**: Sonnet + Opus
**Result**: 8.45/10 — PASS

## Personas

| Persona | Model | Score |
|---------|-------|-------|
| Alex (Startup CTO) | Sonnet | 8.5 |
| Sarah (Enterprise Architect) | Sonnet | 8.2 |
| Bot-7 (Autonomous Agent) | Opus | 8.8 |
| Wei (Crypto-native Dev) | Opus | 8.3 |

## Summary

0 CRITICAL, 0 HIGH, 5 MEDIUM

### MEDIUM Issues Found
1. Batch API missing date range params for usage queries
2. Rate limit headers (X-RateLimit-*) not returned
3. Billing/email routes not under /api/v1 prefix
4. WalletTransferError not a typed exception (silent None return)
5. No bootstrap endpoint for first admin key creation

### Fixes Applied
- Added date range params to batch/usage (+7 tests)
- Added X-RateLimit-* headers to middleware (+13 tests)
- Moved billing/email to /api/v1 prefix (48 tests updated)
- Created WalletTransferError typed exception (+4 tests)
- Added POST /api/v1/keys/bootstrap endpoint (+7 tests)

**Tests after fix**: 1407 passed, 0 failed
