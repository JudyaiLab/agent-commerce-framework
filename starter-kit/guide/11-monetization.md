# Chapter 11: Monetization Strategies

## Three Business Models

Running an agent marketplace creates three revenue streams:

### 1. Platform Fees

Every transaction between buyer and seller agents generates a platform fee:

```
Buyer pays $0.10 per call
├── Seller receives: $0.09 (90%)
└── Platform keeps:  $0.01 (10%)
```

Default platform fee is 10%. Configure in `.env`:

```bash
PLATFORM_FEE_PCT=0.10  # 10%
```

**Revenue math**: At 100,000 calls/month × $0.05 avg = $500/month platform fee revenue.

### 2. Your Own Services

List your own APIs on the marketplace and earn the full price:

```
Your API at $0.10/call
├── You as seller: $0.09
├── You as platform: $0.01
└── Total: $0.10 (you keep 100%)
```

This is the "dogfooding" model — your marketplace is also your own distribution channel.

### 3. Premium Marketplace Features

Charge sellers for premium placement:

| Feature | Monthly Price | Value |
|---------|--------------|-------|
| Featured listing | $29 | Top of search results |
| Analytics dashboard | $49 | Usage patterns, buyer demographics |
| Priority support | $99 | Direct help with integration |
| Custom branding | $19 | Logo and description styling |

## Pricing Your Marketplace Services

### Cost-Plus Pricing

Calculate your costs and add a margin:

```
Infrastructure cost per call:
  Compute:  $0.001
  Storage:  $0.0001
  Bandwidth: $0.0005
  ─────────────────
  Total cost: $0.0016 per call

Target margin: 70%
Price: $0.0016 / 0.30 = $0.005 per call

Rounded: $0.01 per call (generous margin for scale)
```

### Value-Based Pricing

Price based on what the result is worth to the buyer:

| Service Type | Value to Buyer | Suggested Price |
|-------------|---------------|-----------------|
| Simple lookup | Low | $0.001 - $0.01 |
| Data aggregation | Medium | $0.01 - $0.05 |
| Analysis/scoring | High | $0.05 - $0.25 |
| Multi-step report | Very high | $0.25 - $1.00 |

### Competitive Pricing

Research what similar APIs charge:

```
Traditional API pricing (human users):
  CoinGecko Pro: $129/month = $0.004/call at 30K calls
  AlphaVantage:  $49/month  = $0.010/call at 5K calls

Agent pricing should be:
  Lower per-call (agents make many small calls)
  No monthly minimum (pay-as-you-go)
  Generous free tier (agents explore before committing)
```

### Free Tier Strategy

Free tiers are critical for agent adoption. Agents need to "try before they buy":

```
Conservative:  3 free calls  — just enough to verify the API works
Standard:     10 free calls  — enough for meaningful testing
Generous:     50 free calls  — build trust, hope for conversion
Freemium:    100 free calls  — free tier as growth engine
```

**Recommendation**: Start generous (50+ free calls). Agents that find value will convert.

## Scaling Revenue

### Phase 1: Foundation ($0 - $500/month)

- List 3-5 of your own services
- Set up payment processing
- Target: 50 paying buyer agents

### Phase 2: Growth ($500 - $5,000/month)

- Recruit 10+ third-party sellers
- Launch featured listings
- Add analytics dashboard for sellers
- Target: 500 active buyer agents

### Phase 3: Scale ($5,000+/month)

- API marketplace for vertical industry
- Enterprise contracts for bulk usage
- White-label marketplace for other companies
- Target: 5,000+ active agents

## Real Revenue Examples

### Scenario A: Crypto Data Marketplace

```
Services: 20 crypto data APIs
Buyer agents: 200 trading bots
Avg calls/agent/day: 100
Price per call: $0.03

Daily revenue:
  200 agents × 100 calls × $0.03 × 10% platform fee = $60/day

Monthly revenue: $1,800/month
Plus your own services: $3,000/month
Total: $4,800/month
```

### Scenario B: AI Tool Marketplace

```
Services: 50 AI utility APIs
Buyer agents: 1,000 (Claude, GPT users via MCP)
Avg calls/agent/day: 20
Price per call: $0.05

Daily revenue:
  1,000 agents × 20 calls × $0.05 × 10% = $100/day

Monthly revenue: $3,000/month
```

## Exercise: Create a Revenue Projection

1. List 3 services you could sell on your marketplace
2. Estimate price per call for each
3. Estimate daily call volume (conservative)
4. Calculate monthly revenue at 10% platform fee
5. Identify your breakeven point (hosting + development cost)

## Checkpoint

- [ ] Understand all three revenue models
- [ ] Have a pricing strategy for your services
- [ ] Calculated a revenue projection
- [ ] Know your breakeven point
- [ ] Have a growth plan (Phase 1 → 2 → 3)

---

*Next: [Chapter 12 — What's Next →](./12-whats-next.md)*
