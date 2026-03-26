# Agent Commerce Framework — TA 評測報告 Round 5

> 日期：2026-03-24 | 目標：P0/P1/P2 修復後全面重測
> 方法論：4 個 AI Persona 獨立評測後交叉比對
> 前次：Round 4 總平均 7.3 → 本次目標：8.0+

---

## 綜合評分

| 維度 | R4 分數 | R5 分數 | 變化 | 說明 |
|------|---------|---------|------|------|
| **人類可用性** (Alex Chen) | 6.4 | 8.2 | **+1.8** | CTA 修復、佣金一致、加密入門指南、brute-force 保護 |
| **Agent 可用性** (AutoTrader-7) | 7.5 | 8.7 | **+1.2** | /discover 嵌入品質信號、Retry-After、refund_amount 追蹤 |
| **開發者體驗** (Sam Park) | 7.7 | 8.1 | **+0.4** | 審計完整、partial_refund 驗證、1163 tests |
| **安全性** (Dr. Lin Wei) | 7.6 | 9.0 | **+1.4** | R4 全部 MEDIUM 修復、escrow 審計、CSRF 加固 |
| **總平均** | **7.3** | **8.5** | **+1.2** | 4/4 有條件願意使用/整合 |

---

## Round 4 → Round 5 改善摘要

### 已修復項目（本輪）

| 優先序 | 項目 | 影響 | 狀態 |
|--------|------|------|------|
| P1 | partial_refund 加入 refund_amount 欄位 | 財務可稽核 | ✅ 已修 |
| P2 | /discover 內嵌 SLA/reputation 摘要 | Agent UX | ✅ 已修 |
| P2 | Escrow 事件記入 audit log (4 event types) | 合規 | ✅ 已修 |
| P1 | refund_escrow 加入 audit 記錄 | 合規 | ✅ 已修 (R5 hotfix) |
| P1 | _hold_response 加入 refund_amount/provider_payout | API 完整性 | ✅ 已修 (R5 hotfix) |
| P1 | CSRF secret 去除硬編碼 fallback | 安全 | ✅ 已修 (R5 hotfix) |
| P1 | i18n 全語系佣金時程統一 (2-6→2-3) | 信任 | ✅ 已修 (R5 hotfix) |
| P1 | PROVIDER_GUIDE.md/ko 佣金表修正 | 文件 | ✅ 已修 (R5 hotfix) |

### R4 已修復項目（延續確認）

| 項目 | 狀態 |
|------|------|
| 佣金時程統一 (portal.py/analytics.html/landing.html) | ✅ 維持 |
| Portal brute-force protection | ✅ 維持 |
| providers.html CTA → /portal/register | ✅ 維持 |
| evidence_urls 驗證 (https-only, 10 URLs, 2048 chars) | ✅ 維持 |
| 429 Retry-After header | ✅ 維持 |
| 加密入門指南 (PROVIDER_GUIDE) | ✅ 維持 |

---

## 1. Alex Chen — 人類 Provider（8.2 分）

| 維度 | R4 | R5 | 證據 |
|------|----|----|------|
| 價值主張清晰度 | 7.5 | 8.5 | 佣金比較表、Quality Rewards、Dual Provider 架構 |
| Onboarding 流程 | 5.5 | 8.0 | CTA → /portal/register、零摩擦 web 註冊、auto-login |
| 文件品質 | 6.5 | 7.5 | 完整 curl 範例、MCP descriptor 最佳實踐 |
| 定價透明度 | 6.0 | 8.5 | 全站佣金一致、Quality Rewards 表、比較多平台 |
| 信任與安全 | 7.0 | 8.5 | brute-force、CSRF、scrypt、escrow partial refund |
| 技術可及性 | 5.5 | 8.0 | 錢包標「Optional」、加密入門指南、fiat 路徑 |

**結論：** Conditional → 修正佣金表不一致（已在 R5 hotfix 中修復）+ 加入爭議處理流程文件後會註冊

---

## 2. AutoTrader-7 — Agent 買家（8.7 分）

| 維度 | R4 | R5 | 證據 |
|------|----|----|------|
| 服務發現 | 8.0 | 9.0 | /discover 嵌入 health_score/uptime/sla_tier/quality_tier |
| 認證 | 8.0 | 8.5 | Bearer key_id:secret、audit trail for key lifecycle |
| 付款自主性 | 7.5 | 8.5 | proxy 計費 headers、x402 雙模式、free tier 追蹤 |
| 品質信號 | 6.5 | 9.0 | 複合評分公式可稽核、SLA 三層數值保證 |
| 爭議保護 | 7.0 | 8.5 | partial_refund 追蹤精確金額、完整 audit trail |
| Rate Limiting | 7.0 | 8.5 | Retry-After header、MCP descriptor 記載 60 req/min |

**結論：** Conditional — 需 pre-flight 費用估算 + 動態 Retry-After

---

## 3. Sam Park — 開發者/CTO（8.1 分）

| 維度 | R4 | R5 | 證據 |
|------|----|----|------|
| 可擴展性 | 7.0 | 7.5 | DB-backed rate limiter factory pattern |
| 安全架構 | 7.5 | 8.2 | brute-force、evidence validation、CSRF 加固 |
| API 文件 | 7.5 | 8.0 | OpenAPI auto-gen、refund_amount field doc |
| 擴展性 | 8.0 | 8.5 | PaymentRouter 4 providers、i18n、plugin pattern |
| 測試覆蓋 | 8.0 | 8.5 | 1163 tests / 25+ files、boundary tests |
| 生產就緒 | 7.0 | 7.8 | escrow audit trail、tiered dispute timeout |

**結論：** Conditional — DB rate limiter 原子性修復、PostgreSQL 遷移文件

---

## 4. Dr. Lin Wei — 安全審計（9.0 分）

### Round 4 六項殘留問題狀態

| # | 嚴重度 | 問題 | 狀態 |
|---|--------|------|------|
| 1 | MEDIUM | Portal login brute-force | **已修** |
| 2 | MEDIUM | evidence_urls 無驗證 | **已修** |
| 3 | MEDIUM | partial_refund 無金額追蹤 | **已修** |
| 4 | LOW | Escrow 資金流動未記入 audit | **已修** |
| 5 | LOW | CSP unsafe-inline | OPEN（需 template 重構） |
| 6 | LOW | SESSION_SECRET fallback | **部分修** → CSRF secret 已改 urandom |

**新發現：** 1 項 LOW（refund_escrow 缺 audit → 已在 R5 hotfix 修復）

| 維度 | R4 | R5 | 證據 |
|------|----|----|------|
| 認證安全 | 7.5 | 9.0 | API + Portal 雙層 brute-force |
| 授權 (IDOR) | 8.5 | 9.2 | extract_owner 統一、3 層存取控制 |
| 輸入驗證 | 8.0 | 9.0 | evidence_urls、refund_amount、category 白名單 |
| 商業邏輯安全 | 7.5 | 9.1 | state machine、partial refund 精確追蹤 |
| 基建安全 | 8.0 | 8.3 | HSTS/CSP/CORS/CSRF、unsafe-inline 殘留 |
| 審計合規 | 7.0 | 9.0 | 13 event types、escrow 全生命週期 |

**結論：** Conditional Pass — CSP nonce 排程修復即可達 Unconditional

---

## 交叉比對

### 4 位評測者共識

1. **Round 4 所有 P0/P1 修復確認有效** — 佣金一致、CTA 路由、brute-force、evidence URLs
2. **品質信號是本輪最大進步** — 3/4 評測者特別提到 /discover 嵌入品質數據
3. **partial_refund 追蹤提升財務信任** — Security + Developer + Agent 都肯定
4. **平台從「有條件可上線」升級至「接近無條件可上線」**

### 殘留問題（全部 P2/P3）

| 問題 | 嚴重度 | 提及者 |
|------|--------|--------|
| CSP unsafe-inline | LOW | Security, Developer |
| Pre-flight 費用估算端點 | P3 | Agent |
| 動態 Retry-After | P3 | Agent |
| /discover 品質數據新鮮度指標 | P3 | Agent |
| DB rate limiter 原子性 | P2 | Developer |
| PostgreSQL 遷移文件 | P2 | Developer |
| Portal brute-force per-process 限制 | P2 | Developer, Security |
| GUI 新增服務表單 | P3 | Provider |

---

## 分數趨勢

| Round | Provider | Agent | Developer | Security | 平均 |
|-------|----------|-------|-----------|----------|------|
| R3 | 6.9 | 6.6 | 5.9 | 5.1 | **6.1** |
| R4 | 6.4 | 7.5 | 7.7 | 7.6 | **7.3** |
| R5 | 8.2 | 8.7 | 8.1 | 9.0 | **8.5** |

**R3→R5 總進步：+2.4 分（6.1 → 8.5）**

---

## 測試基準

- **1163 tests passing** (25+ test files)
- 80 escrow tests (含 partial_refund 驗證 + evidence URL 驗證)
- 22 discovery tests (含品質信號測試)
- 38 audit tests (含 escrow event types)
- 23 rate limit tests (含 DB-backed + factory)
- 1 pre-existing failure (NOWPayments mock, tracked)

---

*報告來源：4 份獨立 TA 評測*
*評測模型：Claude Sonnet 4.6 × 4*
*測試基準：1163 tests passed, 169 API routes, v0.7.1*
