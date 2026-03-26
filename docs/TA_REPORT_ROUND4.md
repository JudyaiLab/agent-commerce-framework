# Agent Commerce Framework — TA 評測報告 Round 4

> 日期：2026-03-24 | 目標：Agent Provider System 全面評測
> 方法論：4 個 AI Persona 獨立評測後交叉比對
> 前次：Round 3 總平均 6.1 → 本次目標：修復所有 CRITICAL 後重測

---

## 綜合評分

| 維度 | R3 分數 | R4 分數 | 變化 | 說明 |
|------|---------|---------|------|------|
| **人類可用性** (Alex Chen) | 6.9 | 6.4 | -0.5 | Portal 存在但 CTA 仍指向錯誤頁面，佣金時程不一致 |
| **Agent 可用性** (AutoTrader-7) | 6.6 | 7.5 | +0.9 | 結構化爭議、SLA、MCP 描述均大幅改善 |
| **開發者體驗** (Sam Park) | 5.9 | 7.7 | +1.8 | OpenAPI 自動生成、1238 測試、DB rate limiter |
| **安全性** (Dr. Lin Wei) | 5.1 | 7.6 | +2.5 | 9 項 CRITICAL 全部修復，無新 CRITICAL |
| **總平均** | **6.1** | **7.3** | **+1.2** | 4 位中 3 位有條件願意使用/整合 |

---

## 1. Alex Chen — 人類 Provider（6.4 分）

**維度明細：**

| 維度 | 分數 | 證據 |
|------|------|------|
| 價值主張清晰度 | 8.5 | 0%→5%→10% 佣金階梯 + Quality Rewards (6%-8%) 清楚呈現 |
| Onboarding 流程 | 5.5 | Portal 存在，但 providers.html 的 CTA 仍指向 /api-docs，非 /portal/register |
| 文件品質 | 7.5 | PROVIDER_GUIDE.md 通過 QA 8.5 分，但與 FAQ 關於加密錢包的說法矛盾 |
| 定價透明度 | 7.0 | Landing 說 Months 2-6=5%，Pricing 說 Months 2-3=5%，不一致 |
| 信任與安全 | 7.0 | scrypt + HMAC sessions + CSRF + escrow，但無 Privacy Policy 連結 |
| 技術可及性 | 5.0 | FAQ 說不需加密錢包，PROVIDER_GUIDE 說需要 MetaMask，矛盾 |

**R3→R4 改善：** Portal 完整上線、CSRF 保護、scrypt 密碼、referral 系統、drip email
**殘留阻塞：**
1. providers.html CTA 仍指向 /api-docs（Round 3 同一問題）
2. 佣金時程 Landing vs Pricing 不一致（2-6 月 vs 2-3 月）
3. 加密錢包需求的文件矛盾
4. Portal 無 GUI 新增服務（仍需 curl）

**結論：** Conditional — 修復 CTA + 統一佣金說明 + 加密入門指南後會註冊

---

## 2. AutoTrader-7 — Agent 買家（7.5 分）

**維度明細：**

| 維度 | 分數 | 證據 |
|------|------|------|
| 服務發現 | 8 | /discover 支援全文搜尋、分類、標籤、價格區間、付款方式篩選 |
| 認證 | 9 | Bearer key_id:secret，單一 POST 建 key，無 OAuth/CAPTCHA |
| 付款自主性 | 6 | 預付餘額扣款零摩擦，但充值需人類操作（NOWPayments checkout URL） |
| 品質信號 | 7 | SLA 3 tier 可查，但 /discover 回應未內嵌品質分數 |
| 爭議保護 | 9 | 結構化類別、證據提交、供應商回應、管理員仲裁（3 種結果） |
| Rate Limiting | 8 | Token bucket + DB-backed sliding window，MCP 公告 60 req/min |

**R3→R4 改善：** MCP 描述升級（per-service schema）、結構化爭議機制、SLA 合規查詢、tiered 爭議超時
**殘留阻塞：**
1. 錢包充值仍需人類（CRITICAL for autonomy）
2. Escrow 非自動建立（需手動 POST，proxy 不自動觸發）
3. /discover 未內嵌 SLA/reputation（需額外 round trip）

**新發現：**
- 429 回應缺少 Retry-After header
- 爭議超時預設偏向供應商（auto-release to provider），對買家不利
- /discover 無法按 uptime/reliability 排序

**結論：** Conditional — 需程式化充值路徑 + proxy 自動建 escrow

---

## 3. Sam Park — 開發者/CTO（7.7 分）

**維度明細：**

| 維度 | 分數 | 證據 |
|------|------|------|
| 可擴展性 | 7 | DB-backed rate limiter (factory pattern)，但 SQLite 仍為預設 |
| 安全架構 | 8 | scrypt hashing、IDOR 修復、SSRF 防護、brute-force on API auth |
| API 文件 | 8 | FastAPI 自動生成 OpenAPI 3.1 @ /docs + /redoc，169 routes |
| 擴展性 | 8 | PaymentRouter 4 providers、模組化架構、plugin pattern |
| 測試覆蓋 | 8 | 1238 tests / 25+ test files，含 escrow/SLA/commission/rate_limit |
| 生產就緒 | 7 | SLA enforcement、audit logging、webhooks、health monitoring |

**R3→R4 改善：**
- OpenAPI/Swagger 自動生成（R3 完全沒有 → 現在 /docs 和 /redoc 都可用）
- API key scrypt hashing（R3 明文 → 現在 OWASP 級別）
- 測試從 ~800 增至 1238（+55%）
- 支付路由器支援 4 provider（x402/NOWPayments/Stripe ACP/AgentKit）
- SLA 3 tier 強制執行 + 違規追蹤
- DB-backed rate limiter 可選（水平擴展）

**殘留阻塞：**
- SQLite 仍為預設（需 PostgreSQL 遷移指南）
- CSP 含 unsafe-inline（XSS 保護被中和）
- Portal login 無 brute-force protection（API auth 有，portal 沒有）

**結論：** Conditional — 如果加上 PostgreSQL 文件和 portal 安全修復，信任分從 4→7.7

---

## 4. Dr. Lin Wei — 安全審計（7.6 分）

### Round 3 九項 CRITICAL 修復狀態

| # | 漏洞 | 狀態 | 證據 |
|---|------|------|------|
| 1 | IDOR: 讀取任意 Provider email/wallet | **已修** | `_provider_response()` 只在 is_owner=True 時顯示 PII |
| 2 | IDOR: 讀取任意 escrow hold | **已修** | `_can_access_hold()` 驗證 buyer/provider ownership |
| 3 | IDOR: 以任意 provider_id 查 holds | **已修** | 非 admin 結果過濾 buyer_id/provider_id |
| 4 | IDOR: 偽造 buyer_id | **已修** | buyer_id 從 extract_owner() 伺服器端設定 |
| 5 | IDOR: dispute 任何人的 hold | **已修** | 檢查 buyer_id == owner_id |
| 6 | SSRF: 無私有 IP 阻擋 | **已修** | ipaddress 模組檢查 private/loopback/link_local/reserved |
| 7 | TOCTOU: 日交易上限 | **已修** | 原子 UPDATE WHERE (daily_tx_used + ?) <= cap |
| 8 | SQL 動態欄位注入 | **已修** | allowed set 白名單所有 update_* 方法 |
| 9 | 3 帳號下架 Provider | **已修** | 閾值升至 5 + 需交易紀錄 + 去重 |

**9/9 CRITICAL 全部修復**

**維度明細：**

| 維度 | 分數 | 證據 |
|------|------|------|
| 認證安全 | 7.5 | scrypt + timing-safe compare + API brute-force，但 portal login 無保護 |
| 授權 (IDOR) | 8.5 | extract_owner() 統一來源，所有端點一致檢查 |
| 輸入驗證 | 8.0 | 參數化查詢、錢包/DID regex、排序白名單，但 evidence_urls 無驗證 |
| 商業邏輯安全 | 7.5 | buyer_id 伺服器設定、tiered escrow，但 partial_refund 無金額追蹤 |
| 基建安全 | 8.0 | 7 項 security headers、CORS 預設限制、CSRF、follow_redirects=False |
| 審計合規 | 7.0 | AuditLogger 存在，但 escrow 資金流動未記入審計日誌 |

**新發現（無 CRITICAL）：**

| 嚴重度 | 說明 |
|--------|------|
| MEDIUM | Portal login 無 brute-force protection（60 req/min 太寬鬆） |
| MEDIUM | evidence_urls 無驗證（scheme/count/length） |
| MEDIUM | partial_refund 無金額追蹤（財務可稽核性缺口） |
| LOW | escrow 資金流動未記入 audit log |
| LOW | CSP unsafe-inline 弱化 XSS 防護 |
| LOW | SESSION_SECRET fallback 重啟失效 |

**結論：** Conditional — 2-3 天修復後可上線

---

## 交叉比對（4 位評測者共識問題）

### 3+ 位評測者共識

| 問題 | 提及者 | 優先序 |
|------|--------|--------|
| Portal login 無 brute-force protection | Security, Developer, Provider | P1 |
| 佣金時程不一致（Landing vs Pricing vs Code） | Provider, Developer | P1 |
| 錢包充值需人類操作 | Agent, Developer, Security | P1 |
| evidence_urls 無驗證 | Security, Agent | P2 |
| /discover 未嵌入品質信號 | Agent, Developer | P2 |

### 全部 4 位共識

1. **Round 3 的 9 項 CRITICAL 全部修復** — 安全態勢大幅改善
2. **商業模式和價值主張仍是最強維度** — 佣金結構、Quality Rewards、Proxy Key
3. **平台從「不可上線」升級到「有條件可上線」** — 3/4 有條件願意使用

---

## 優先修復路線圖

| 優先序 | 項目 | 影響 | 工作量 | 目標分 |
|--------|------|------|--------|--------|
| P0 | 統一佣金時程（Landing/Pricing/Portal/Code） | 信任 | 小 | +0.3 |
| P0 | Portal login brute-force protection | 安全 | 小 | +0.2 |
| P1 | 修正 providers.html CTA → /portal/register | 轉換率 | 小 | +0.3 |
| P1 | evidence_urls scheme/count 驗證 | 安全 | 小 | +0.1 |
| P1 | partial_refund 加入 refund_amount 欄位 | 財務 | 中 | +0.1 |
| P2 | /discover 內嵌 SLA/reputation 摘要 | Agent UX | 中 | +0.3 |
| P2 | 429 回應加 Retry-After header | Agent UX | 小 | +0.1 |
| P2 | 加密入門指南 + 統一文件 | Onboarding | 中 | +0.2 |
| P2 | Escrow 事件記入 audit log | 合規 | 小 | +0.1 |
| P3 | GUI 新增服務表單 | Provider UX | 中 | +0.2 |
| P3 | 程式化充值路徑（on-chain USDC） | Agent 自主 | 大 | +0.5 |

**修復 P0+P1 後預估分數：7.8-8.0**
**修復全部後預估分數：8.5+**

---

## 總結

Round 3 → Round 4: **6.1 → 7.3 (+1.2)**

最大進步：安全性 (+2.5)、開發者體驗 (+1.8)
最需改善：人類 Provider onboarding（CTA/文件一致性）

**平台狀態：從「不可上線」升級至「有條件可上線」**

---

*報告來源：4 份獨立 TA 評測*
*評測模型：Claude Sonnet 4.6 × 3 + 手動評估 × 1*
*測試基準：1238 tests passed, 169 API routes, v0.7.1*
