# Architecture Diagrams

## System Overview

```
┌────────────────────────────────────────────────────────────────┐
│                    Agent Commerce Framework                     │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   │
│  │ Service  │   │ Billing  │   │  Proxy   │   │Discovery │   │
│  │ Registry │   │ Engine   │   │ Router   │   │  Search  │   │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   │
│       │               │               │               │        │
│       └───────────────┼───────────────┼───────────────┘        │
│                       │               │                         │
│                ┌──────▼───────────────▼──────┐                 │
│                │       SQLite Database        │                 │
│                └─────────────────────────────┘                 │
│                       │               │                         │
│  ┌──────────┐   ┌────▼─────┐   ┌────▼─────┐   ┌──────────┐   │
│  │ Identity │   │Settlement│   │  Auth &  │   │Reputation│   │
│  │  (DID)   │   │  Engine  │   │ API Keys │   │ Scoring  │   │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘   │
│                                                                 │
├─────────────────────── Payment Layer ──────────────────────────┤
│                                                                 │
│  ┌────────────┐   ┌────────────┐   ┌────────────────────────┐ │
│  │NOWPayments │   │  PayPal    │   │ x402 + AgentKit (USDC) │ │
│  │  (Crypto)  │   │   (Fiat)   │   │      (On-Chain)        │ │
│  └────────────┘   └────────────┘   └────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
         ▲                                          ▲
         │                                          │
    ┌────┴────────┐                          ┌──────┴──────┐
    │Buyer Agents │                          │Seller Agents│
    │ Claude, GPT │                          │ Your APIs,  │
    │ Custom bots │                          │ Third-party │
    └─────────────┘                          └─────────────┘
```

## Request Flow (Proxy Call)

```
Buyer Agent                    ACF Server                     Seller API
     │                             │                              │
     │  POST /proxy/{svc}/path     │                              │
     │  + buyer_id                 │                              │
     ├────────────────────────────▶│                              │
     │                             │                              │
     │                    ┌────────┤                              │
     │                    │ 1. Auth │                              │
     │                    │ 2. Balance check                      │
     │                    │ 3. Free tier check                    │
     │                    │ 4. SSRF validation                    │
     │                    └────────┤                              │
     │                             │                              │
     │                             │  Forward request             │
     │                             ├─────────────────────────────▶│
     │                             │                              │
     │                             │  Response                    │
     │                             │◀─────────────────────────────┤
     │                             │                              │
     │                    ┌────────┤                              │
     │                    │ 5. Deduct buyer                       │
     │                    │ 6. Credit seller                      │
     │                    │ 7. Log usage                          │
     │                    └────────┤                              │
     │                             │                              │
     │  Response + billing headers │                              │
     │◀────────────────────────────┤                              │
     │  X-ACF-Amount: 0.05        │                              │
     │  X-ACF-Balance: 4.95       │                              │
```

## Payment Flow (Crypto Deposit)

```
Buyer Agent              ACF Server            NOWPayments        Blockchain
     │                       │                      │                  │
     │  POST /deposits       │                      │                  │
     │  {amount: 10}         │                      │                  │
     ├──────────────────────▶│                      │                  │
     │                       │  Create invoice      │                  │
     │                       ├─────────────────────▶│                  │
     │                       │  checkout_url        │                  │
     │                       │◀─────────────────────┤                  │
     │  checkout_url         │                      │                  │
     │◀──────────────────────┤                      │                  │
     │                       │                      │                  │
     │  (pays in crypto)     │                      │                  │
     │───────────────────────┼──────────────────────┼─────────────────▶│
     │                       │                      │                  │
     │                       │                      │  Confirms        │
     │                       │                      │◀─────────────────┤
     │                       │                      │                  │
     │                       │  IPN: confirmed      │                  │
     │                       │  HMAC-SHA512 signed  │                  │
     │                       │◀─────────────────────┤                  │
     │                       │                      │                  │
     │                       │  Verify signature    │                  │
     │                       │  Credit balance      │                  │
     │                       │                      │                  │
     │  GET /balance         │                      │                  │
     ├──────────────────────▶│                      │                  │
     │  {balance: 10.00}     │                      │                  │
     │◀──────────────────────┤                      │                  │
```

## Multi-Agent Swarm

```
                    ┌───────────────┐
                    │ Orchestrator  │
                    │ (coordinator) │
                    └──────┬────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼─────┐     │     ┌──────▼─────┐
       │  Discovery  │     │     │  Reporter  │
       │   Agent     │     │     │   Agent    │
       │ (find svcs) │     │     │ (summarize)│
       └──────┬──────┘     │     └────────────┘
              │            │
              ▼            │
       ┌─────────────┐    │
       │  Quality    │    │
       │   Agent     │    │
       │ (evaluate)  │    │
       └──────┬──────┘    │
              │            │
              ▼            │
       ┌─────────────┐    │
       │   Buyer     │────┘
       │   Agent     │
       │ (purchase)  │
       └─────────────┘

Flow: Discover → Evaluate → Buy → Report
```

## Production Deployment

```
                Internet
                   │
                   ▼
         ┌─────────────────┐
         │   Cloudflare    │ (optional CDN/DDoS)
         │                 │
         └────────┬────────┘
                  │
         ┌────────▼────────┐
         │     Nginx       │
         │  ┌───────────┐  │
         │  │ SSL/TLS   │  │
         │  │ Rate limit │  │
         │  │ Headers    │  │
         │  └───────────┘  │
         └────────┬────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│  ACF  │   │  ACF  │   │  ACF  │ (scale-out)
│ App 1 │   │ App 2 │   │ App 3 │
└───┬───┘   └───┬───┘   └───┬───┘
    │           │           │
    └─────────┬─┘───────────┘
              │
    ┌─────────▼─────────┐
    │    PostgreSQL      │ (or SQLite for single-server)
    └───────────────────┘
              │
    ┌─────────▼─────────┐
    │      Redis        │ (cache + rate limiting)
    └───────────────────┘
```
