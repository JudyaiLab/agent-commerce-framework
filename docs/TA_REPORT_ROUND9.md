# TA Evaluation Round 9

**Date**: 2026-03-25
**Models**: Sonnet + Opus
**Result**: 7.25/10

## Personas

| Persona | Model | Score |
|---------|-------|-------|
| Marcus (API Architect) | Sonnet | 8.0 |
| Priya (Fintech PM) | Sonnet | 8.0 |
| Jin (Security Researcher) | Opus | 6.5 |
| River (Non-binary ML Engineer) | Opus | 6.5 |

## Summary

0 CRITICAL, 2 HIGH, 12 MEDIUM

### HIGH Issues Found
1. `julianday()` SQLite-only function in DatabaseRateLimiter — breaks PostgreSQL
2. Per-key rate limit `check_rate_limit()` existed but never wired into middleware

### Key MEDIUM Issues
- ETH address validation missing (accepts any string)
- Escrow no max amount cap
- Brute-force counter in-memory (not multi-worker safe)
- DNS rebinding TOCTOU in webhooks
- Settlement no duplicate prevention

### Fixes Applied
- julianday → epoch float for PG compatibility
- Per-key rate limit wired into middleware Layer 2
- ETH address validation with 0x prefix + hex check (+14 tests)
- Escrow max amount cap $100K (+4 tests)
- Brute-force → DB-backed DatabaseRateLimiter + SSRF DNS pinning fix

**Tests after fix**: 1431 passed, 0 failed
