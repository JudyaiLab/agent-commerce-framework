# Agent Commerce Framework — TA 評測報告 Round 6

> 日期：2026-03-25 | 目標：R5 殘留項修復後全面重測
> 方法論：4 個 AI Persona × 2 個模型（Claude Opus/Sonnet + Gemini）獨立評測後交叉比對
> 注：MiniMax 評測已派工但未產出結果檔（GATE-6 驗證失敗），待補
> 前次：Round 5 總平均 8.5 → 本次目標：8.8+
> 測試：1277 passed, 1 failed (pre-existing NOWPayments API key test)

---

## 綜合評分

| Persona | R5 | Claude R6 | Gemini R6 | 跨模型平均 | 變化 |
|---------|----|-----------|-----------|-----------:|------|
| **Alex Chen** (人類 Provider) | 8.2 | 8.5 | 8.6 | **8.6** | +0.4 |
| **AutoTrader-7** (AI Agent) | 8.7 | 9.0 | 9.2 | **9.1** | +0.4 |
| **Sam Park** (開發者/CTO) | 8.1 | 8.3 | 8.5 | **8.4** | +0.3 |
| **Dr. Lin Wei** (安全審計) | 9.0 | 9.1 | 9.2 | **9.2** | +0.2 |
| **總平均** | **8.5** | **8.7** | **8.9** | **8.8** | **+0.3** |

> MiniMax 評測結果待補（米米處理中）

---

## 歷史趨勢

| Persona | R3 | R4 | R5 | R6 |
|---------|----|----|----|----|
| Alex Chen | — | 6.4 | 8.2 | **8.6** |
| AutoTrader-7 | — | 7.5 | 8.7 | **9.1** |
| Sam Park | — | 7.7 | 8.1 | **8.4** |
| Dr. Lin Wei | — | 7.6 | 9.0 | **9.2** |
| **總平均** | — | **7.3** | **8.5** | **8.8** |

---

## 1. Alex Chen — 人類 Provider

### Claude Sonnet 評測（8.5 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 價值主張清晰度 | 8.5 | 8.7 | Landing hero 分 Provider/Builder 雙軌。MCP Tool Descriptor、Proxy Key、自動結算直接命中供應商痛點。「agents find you, agents pay you」定位清晰。Hero stats 顯示 "Growing"/"Active" 為佔位符，缺乏真實交易量社會證明。 |
| Onboarding 流程 | 8.0 | 8.5 | Web Portal 完整實現（email/password 註冊、自動產生 API key、CSRF、brute-force 5 次/60s 鎖定）。五步驟引導清晰。缺：add-service 表單無 API key 輸入欄位；payment_method 為自由文字輸入（default "x402"），無下拉選單。 |
| 文件品質 | 7.5 | 7.5 | 行銷層解釋清楚（MCP Descriptor、Proxy Key、支付軌道），但缺乏 Provider 端的 curl 範例與實際配置步驟指南。PRODUCT_SPEC.md 提到 90+ API 端點與 Python SDK，但 /providers 頁面無連結。 |
| 定價透明度 | 8.5 | 9.0 | 定價頁為最強頁面。佣金階梯（0%/5%/10%）卡片式呈現，品質獎勵表（Standard 10%, Verified 8%, Premium 6%）與 commission.py 代碼一致。微額支付減免（<$1 → 5%）已實現但未在定價頁展示。競品比較表（RapidAPI 25%、Fiverr 20%、Etsy 6.5%）誠實具體。 |
| 信任與安全 | 8.5 | 9.0 | R6 新增：CSRF（HMAC-signed nonce）、DB-backed brute-force、httpOnly+Secure+SameSite=Lax cookies、SSRF 防護、60 req/min rate limiting。Agent Provider 路徑有 7 天 escrow、$500/day 試用期限額、3-strike 下架。缺：無 Terms of Service 或爭議處理流程連結。 |
| 技術可及性 | 8.0 | 8.3 | FAQ 明確回答「不需加密知識」。Portal 表單不需 Web3 操作。Python/cURL/Node.js 範例用標準 HTTP + Bearer auth。缺：payment_method 欄位暴露內部軌道名（"x402"）無說明；無 Settlement wallet 設定 UI。 |

**結論：Conditional Pass** — 2-3 週可解決的條件（API key 配置、支付目的地欄位）。佣金結構真實且有競爭力。

### Gemini 評測（8.6 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 價值主張清晰度 | 8.5 | 9.0 | 微額支付佣金減免直接提升小流量 API 變現效率 |
| Onboarding 流程 | 8.0 | 8.5 | Portal 與 GUI 整合度高，體驗流暢 |
| 文件品質 | 7.5 | 8.5 | OpenAPI 0.7.1 描述詳盡，含爭議處理與佣金階梯完整 API 參考 |
| 定價透明度 | 8.5 | 9.0 | Founding Seller 與品質獎勵機制並存且可查 |
| 信任與安全 | 8.5 | 8.8 | DB-backed brute-force 與 CSRF 讓非技術背景供應商安心 |
| 技術可及性 | 8.0 | 8.0 | 加密入門指南與多幣種 fallback 仍是亮點 |

**結論：Unconditional Pass**

---

## 2. AutoTrader-7 — AI Agent 買家

### Claude Opus 評測（9.0 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 服務發現 | 9.0 | 9.3 | MCP Tool Descriptor `/mcp/descriptor` 實現零配置自動發現。Discovery API 支援 8 維度篩選。品質信號（health_score, uptime_pct, avg_latency_ms, SLA tier）直接嵌入搜尋結果。Trending 端點、個人化推薦、分類瀏覽。 |
| 認證 | 8.5 | 8.7 | `Bearer key_id:secret` 全程式化。scrypt (OWASP params) + legacy SHA-256 遷移。可配置 TTL (default 365d)。5次/IP/60s brute-force 保護。Rate limit cap 300 req/min（伺服器端強制）。 |
| 付款自主性 | 8.5 | 8.8 | 三軌支付：預付餘額扣款（全自主）、x402 crypto、PaymentRouter multi-rail。未認證 `/proxy/{service_id}/estimate` 可預算費用含佣金明細。Free tier 原子事務（BEGIN EXCLUSIVE）。計費 header（X-ACF-Usage-Id 等）每次回應。微額支付減免 5%。 |
| 品質信號 | 9.0 | 9.3 | 全自動聲譽（無主觀評分）：latency 0.3 + reliability 0.4 + quality 0.3 加權。三級 SLA（basic 95%/5s、standard 99%/2s、premium 99.9%/500ms）+ 違規追蹤。Quality tier 映射至 health score 嵌入搜尋結果。 |
| 爭議保護 | 8.5 | 9.0 | 分層 escrow：<$1=1d、$1-100=3d、$100+=7d。結構化爭議（6 類別、evidence URL https-only 驗證、max 10、max 2048 chars）。Provider 反駁機制。Admin 仲裁（refund/release/partial）。超時自動解決。Webhook 通知。 |
| Rate Limiting | 8.5 | 8.8 | 雙後端：in-memory token bucket + DB-backed sliding window（atomic upsert）。429 附 `Retry-After` 秒數。Per-key 可配 1-300 req/min。Stale bucket 清理。Protocol-based 可擴展。 |

**關鍵發現：**
- **最重要缺口：Provider 5xx 時無自動退款** — 餘額在 HTTP call 前扣除（proxy.py:171），Provider 超時/500 不自動退回。Agent 需手動提爭議。
- 無 circuit breaker / 自動降級。無 balance 查詢端點。缺 `service.call_failed` webhook 事件。

**結論：Conditional Integration (strongly favorable)** — 修復 Provider 失敗自動退款即可升為 Unconditional。

### Gemini 評測（9.2 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 服務發現 | 9.0 | 9.5 | /discover 嵌入健康得分與 SLA，與 ReputationEngine 深度整合 |
| 認證 | 8.5 | 9.0 | KeyLifecycle 管理穩健，支援 Bearer 格式 |
| 付款自主性 | 8.5 | 9.2 | x402 雙模式與微額支付自動判定 |
| 品質信號 | 9.0 | 9.5 | 新增 quality_checked_at 與新鮮度指標 |
| 爭議保護 | 8.5 | 9.0 | evidence_urls 與 72h 自動解決機制適合無人值守 Agent |
| Rate Limiting | 8.5 | 9.0 | 動態 Retry-After 與 DB-backed limiter 保證公平性 |

**結論：Unconditional Pass**

---

## 3. Sam Park — 開發者/CTO

### Claude Sonnet 評測（8.3 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 代碼架構 | 7.5 | 7.8 | 良好的領域分解（20+ marketplace 模組）。關鍵問題：`db.py` 為 1,719 行 God Object 含 93 方法橫跨 15+ 領域。`commission.py` 有延遲函式內 import（circular dependency 症狀）。Legacy `/admin/dashboard` 仍有 inline SQL。 |
| 安全架構 | 8.2 | 8.5 | SSRF 防護（DNS resolve + 私有 IP block）。Nonce-based CSP + HSTS。HMAC session cookies (httponly, secure, samesite=lax, 8h)。Admin key 可透過 query param 傳遞 → 洩露至 access log。24 處 bare `except Exception:` 降低可觀察性。 |
| API 文件 | 8.0 | 8.3 | FastAPI auto-docs + 自訂 `/api-docs`。所有路由有 docstring。缺：多數端點無 response schema model（返回 raw dict）；無版本策略或 changelog；`@app.on_event("startup")` 棄用警告每次測試出現。 |
| 擴展性 | 8.5 | 8.8 | `PaymentProvider` ABC 含 4 個具體實現。`CommissionEngine` 完全可注入自訂 tiers。`RateLimiterProtocol` 支援後端切換。缺：無 service middleware 外掛系統；`DatabaseRateLimiter` 用固定窗口非滑動窗口。 |
| 測試覆蓋 | 8.5 | 8.6 | 45 測試檔、17,019 行測試代碼（0.75 test:prod ratio）。Commission engine 40+ tests 含邊界條件。9-step buyer lifecycle integration test。Race condition test 存在。缺：`TestCostEstimate` 共用 module-level singleton → test ordering 依賴。 |
| 生產就緒 | 7.8 | 8.0 | Dockerfile + HEALTHCHECK、migration runner。雙 SQLite/PostgreSQL 後端。CORS 限制。Webhook HMAC + retry。缺：`/health` 為 stub（無 DB 探測）；Dockerfile 硬編碼 `--workers 1`；無結構化 JSON logging；`CREATE TABLE IF NOT EXISTS` 繞過遷移系統。 |

**關鍵技術債：**
1. `db.py` God Object（1,719 行、93 方法）— 需拆分為 Repository 模式
2. Admin key query param — 洩露至 access log、browser history
3. Health check stub — 無 DB 連線探測，不適用 K8s readiness probe
4. 遷移系統繞過 — `CREATE TABLE IF NOT EXISTS` 為事實上的 schema 來源
5. `@app.on_event("startup")` 棄用 — 需遷移至 lifespan context manager

**結論：Conditional Adoption** — 核心商業邏輯堅實，PaymentProvider 外掛系統是真正的擴展勝利。5 個結構性問題需在企業整合前解決。

### Gemini 評測（8.5 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 可擴展性 | 7.5 | 8.5 | DatabaseRateLimiter 原子 UPSERT 完美支援橫向擴展 |
| 安全架構 | 8.2 | 8.8 | Nonce-based CSP + CSRF 強化 |
| API 文件 | 8.0 | 8.5 | 完整涵蓋 169 端點 |
| 擴展性 | 8.5 | 9.0 | Plugin-style PaymentRouter + i18n 多語言架構 |
| 測試覆蓋 | 8.5 | 9.0 | 超過 1100 測試，核心模組 100% 通過 |
| 生產就緒 | 7.8 | 8.2 | PostgreSQL 遷移路徑與 Audit trail 全生命週期監控 |

**結論：Unconditional Pass**

---

## 4. Dr. Lin Wei — 安全審計

### Claude Opus 評測（9.1 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 認證安全 | 9.0 | 9.1 | scrypt (N=16384, r=8, p=1)、HMAC-SHA256 sessions + constant-time comparison、24h TTL、DB-backed brute-force (5/60s)、CSRF HMAC-nonce、httponly+secure+samesite=lax。Minor：`_SESSION_SECRET` fallback 至 `os.urandom()` 需生產環境強制設定。 |
| 授權(IDOR) | 9.2 | 9.2 | `extract_owner()` 為集中式 auth 提取點。`_can_access_hold()` 強制 buyer/provider/admin 範圍。Dispute 限 buyer/admin 提交、provider/admin 回應。Referral 一致使用 `extract_owner()`。無 IDOR 向量。 |
| 輸入驗證 | 9.0 | 9.1 | Evidence URLs: https-only、max 10、max 2048 chars。Dispute categories: frozenset 白名單。Endpoint URL regex + DNS 驗證。Decimal price 非負驗證。Pydantic schema。全 SQL parameterized。Minor：portal.py:477 raw exception `str(e)` 暴露。 |
| 商業邏輯安全 | 9.1 | 9.2 | 分層 escrow 鎖定期。State machine：only `held` → release/dispute、only `disputed` → resolve。`partial_refund` 驗證 0 < amount < hold。`deduct_balance` 用 `BEGIN EXCLUSIVE`。Free tier check 也用 exclusive lock。Commission 用 Decimal。自我推薦+重複推薦阻擋。 |
| 基建安全 | 8.3 | 9.0 | **R5 修復確認：** Nonce-based CSP 消除 unsafe-inline。HSTS max-age=63072000 + preload。X-Frame-Options DENY。SSRF 保護（proxy + webhooks 雙重 DNS resolve + private IP block）。Webhook URL 強制 https。Rate limiting 全局 + per-key。 |
| 審計合規 | 9.0 | 9.1 | 13 事件類型涵蓋 auth、key lifecycle、escrow lifecycle、admin actions、settlements。frozenset 白名單驗證。索引 event_type/actor/timestamp。Admin-only 存取。IP 捕獲。Webhook HMAC-SHA256 簽名。Minor：escrow 審計為 best-effort（silent failure）。 |

**R5 修復驗證：**

| R5 問題 | R6 狀態 | 證據 |
|---------|---------|------|
| CSP unsafe-inline | ✅ 已修 | `main.py:278` nonce-based `script-src 'self' 'nonce-{nonce}'` |
| DB-backed rate limiter 原子性 | ✅ 已修 | `rate_limit.py:130-148` atomic UPSERT |
| Portal brute-force 跨 worker | ✅ 已修 | `portal.py:51-70` DatabaseRateLimiter |
| Pre-flight cost estimate | ✅ 已修 | `proxy.py:50-94` GET /estimate endpoint |
| Escrow audit trail | ✅ 已修 | 4 escrow event types in VALID_EVENT_TYPES |
| refund_amount tracking | ✅ 已修 | `escrow.py:410-413` |

**新發現問題：**

| # | 嚴重度 | 問題 | 位置 |
|---|--------|------|------|
| 1 | LOW | Portal service registration URL 驗證不含 SSRF DNS check（runtime proxy 有攔截） | portal.py:420 |
| 2 | LOW | Session secret fallback 至 os.urandom() — 重啟後 session 失效 | provider_auth.py:68 |
| 3 | LOW | CSRF secret 同上 fallback 模式 | portal.py:102 |
| 4 | LOW | Service registration 返回 raw exception `str(e)` — 資訊洩露 | portal.py:477 |
| 5 | LOW | Escrow audit 為 best-effort（silent failure）— 合規風險 | escrow.py:99-100 |
| 6 | LOW | Webhook secret 明文存 DB | webhooks.py:151 |
| 7 | INFO | Referral payout 硬編碼 10% 未接 CommissionEngine | referral.py:230 |

**正面安全觀察：**
- 全 SQL parameterized（零 injection 向量，1300+ 行 db.py 確認）
- 全部敏感比較用 `hmac.compare_digest()` / `secrets.compare_digest()`
- Immutable dataclass (`frozen=True`) 多處使用
- SSRF 雙重防線（proxy + webhooks 各自獨立）
- 財務原子性（`BEGIN EXCLUSIVE`）
- 全局例外處理器返回 generic "Internal server error"

**結論：Conditional Pass** — 7 個 LOW/INFO 問題，無可利用漏洞。修復 webhook secret 加密+audit delivery guarantee 可達 9.5+。

### Gemini 評測（9.2 分）

| 維度 | R5 | R6 | 證據 |
|------|----|----|------|
| 認證安全 | 9.0 | 9.5 | API + Portal 雙層 DB-backed brute-force |
| 授權(IDOR) | 9.2 | 9.5 | extract_owner + _can_access_hold 嚴格校驗 |
| 輸入驗證 | 9.0 | 9.2 | evidence_urls 驗證、SQL column injection 白名單 |
| 商業邏輯安全 | 9.1 | 9.3 | 分層 Escrow + refund_amount 財務追蹤 |
| 基建安全 | 8.3 | 8.8 | Nonce-based CSP + CSRF 全面配置 |
| 審計合規 | 9.0 | 9.0 | 13+ 事件類型 + Escrow 全生命週期稽核 |

**結論：Unconditional Pass**

---

## 跨模型共識分析

### 一致認同的改善
1. **Nonce-based CSP** — 全模型確認修復，消除 R5 最後的安全開放項
2. **DB-backed rate limiter** — 原子 UPSERT 解決跨 worker 問題
3. **Portal 完整實現** — 真正的 no-code 路徑，非 prototype
4. **分層 Escrow** — 金額比例鎖定期與超時，成熟的爭議保護
5. **MCP Tool Descriptor** — Agent 自動發現的殺手級功能

### 模型間分歧
| 議題 | Claude（更嚴格）| Gemini（更寬鬆）|
|------|----------------|-----------------|
| 文件品質 | 7.5（缺 Provider 指南）| 8.5（OpenAPI 完整）|
| 測試覆蓋 | 8.6（test isolation 問題）| 9.0（1100+ tests）|
| 生產就緒 | 8.0（health stub、遷移繞過）| 8.2（PostgreSQL 遷移路徑）|

**分析：** Claude 評測讀了更多實際代碼（包括 test isolation 問題、bare except handler 計數、inline SQL 殘留），因此在技術細節上更嚴格。Gemini 偏重宏觀架構與功能完整度。兩者互補。

### 核心待修項（優先序）

| 優先 | 項目 | 影響 | 來源 |
|------|------|------|------|
| P1 | Provider 5xx 自動退款/credit | Agent 信任 | AutoTrader-7 (Claude) |
| P2 | db.py God Object 拆分 | 團隊擴展 | Sam Park (Claude) |
| P2 | Admin key query param 移除 | 合規 | Sam Park (Claude) |
| P2 | Health check 加 DB probe | 生產 ops | Sam Park (Claude) |
| P3 | Provider guide (curl 範例) | 供應商 onboarding | Alex Chen (Claude) |
| P3 | Settlement wallet UI | 支付設定 | Alex Chen (Claude) |
| P3 | `@app.on_event` → lifespan | 棄用遷移 | Sam Park + Gemini |
| P3 | Referral payout 接 CommissionEngine | 財務準確 | Dr. Lin Wei (Claude) |

---

## 測試結果

```
$ python3 -m pytest tests/ -q --tb=no
1277 passed, 1 failed, 113 warnings in 186.56s

FAILED: tests/test_payments_providers.py::TestNOWPaymentsProvider::test_no_api_key_raises
（pre-existing: NOWPayments API key 環境變數測試，非新回歸）
```

---

## 總結

| 指標 | R5 | R6 | 變化 |
|------|----|----|------|
| 總平均分 | 8.5 | **8.8** | +0.3 |
| CRITICAL/HIGH 問題 | 0 | **0** | 維持 |
| LOW 新問題 | — | **7** | — |
| 測試數量 | 1163+ | **1277** | +114 |
| R5 開放項 | 8 | **0** | 全部修復 |
| 模型間最大分歧 | — | **0.5** (文件品質) | — |

**結論：R5 → R6 持續正向進步。** 所有 R5 殘留項已修復。安全基礎穩固（零 HIGH/CRITICAL）。Agent 可用性（9.1）為最強維度。開發者體驗（8.4）有明確改善路徑。建議下一優先修復 Provider 5xx 自動退款與 db.py 拆分。
