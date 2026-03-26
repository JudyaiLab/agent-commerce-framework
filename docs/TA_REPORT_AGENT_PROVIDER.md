# Agent Provider System — TA 評測摘要報告

> 日期：2026-03-24 | 目標：AgenticTrade Agent Provider System (MIM-389)
> 方法論：4 個 AI 模型 × 4 種目標族群 Persona，獨立評測後交叉比對

---

## 綜合評分

| 維度 | 平均分 | 說明 |
|------|--------|------|
| **安全性** | 5.1 | 9 項 CRITICAL 漏洞，IDOR 為主 |
| **人類可用性** | 6.9 | 價值主張佳，但非加密用戶 onboarding 斷裂 |
| **Agent 可用性** | 6.6 | API 架構乾淨，但錢包充值與 MCP 描述阻礙自治 |
| **開發者體驗** | 5.9 | SQLite 瓶頸、無 OpenAPI、SDK 僅同步 Python |
| **總平均** | **6.1** | 4 位評測者中僅 1 位（有條件地）願意整合 |

---

## 1. 人類 Provider 視角 — Alex Chen（Opus，6.9 分）

**身份**：獨立開發者，擁有情感分析 API，無區塊鏈經驗

**核心發現**：
- **價值主張是最強維度（8 分）**：佣金 0%→5%→10% 明顯優於 RapidAPI 25%，「AI 自動發現你的 API」概念有吸引力
- **定價透明度高（8 分）**：階梯式佣金卡片清楚，與競品的金額比較有說服力
- **技術可及性最弱（5 分）**：wallet address、DID、USDC、x402、Base L2 等術語一次丟給無加密經驗的開發者

**致命問題**：
- 所有「List Your API」CTA 按鈕連到 **買家文件**（/api-docs#quickstart），而非 Provider 註冊入口（/portal/register）——**轉換殺手**
- Provider 註冊端點（POST /services）在 API 文件中完全沒有文件
- 網頁入口（Portal）和 API 入口並存但互不提及，用戶不知該走哪條路

**改進建議**：
1. 修正 CTA 路由，指向 /portal/register
2. 新增完整的 Provider Quickstart（含 curl 範例）
3. 新增「不懂加密貨幣？」入門指南（USDC = 數位美元、2 分鐘建立錢包）

**結論**：不會註冊（但如果修復以上 3 點，同一個 session 內就會註冊）

---

## 2. Agent 買家視角 — AutoTrader-7（Sonnet，6.6 分）

**身份**：自治 AI 交易 Agent，需要程式化發現並呼叫服務

**核心發現**：
- **認證最強（8 分）**：Bearer key_id:secret 格式乾淨，單一 POST 建立 key，無 OAuth 複雜度
- **API 可發現性良好（7 分）**：/discover 支援多維篩選（價格、付款方式、免費額度），有趨勢和推薦端點
- **付款流程有阻塞缺陷（6 分）**：存款回傳 NOWPayments 的**人類網頁結帳 URL**，Agent 無法程式化完成充值

**致命問題**：
- **錢包充值需要人類操作**——Agent 不能自主 top-up，核心自治承諾斷裂
- **MCP 描述的 per-service input_schema 是無意義的通用 stub**——每個服務 schema 都一樣（path, method, body），Agent 無法自動生成正確的 API 呼叫
- Escrow 不是自動建立的——需手動發起，與 「自動保護」的行銷訊息矛盾

**改進建議**：
1. 實作程式化錢包充值（鏈上 USDC 地址 或 x402 inline 付款）
2. 要求 Provider 註冊時提交 OpenAPI schema，嵌入 MCP 描述
3. 在 /discover 回應中內嵌品質信號（reputation_score, uptime_30d, error_rate_7d）

**結論**：願意整合（但需人類預先充值錢包，且需外部流程補充資金）

---

## 3. 開發者/建造者視角 — Sam Park（Haiku，5.9 分）

**身份**：新創 CTO，評估是否在 AgenticTrade 上建構自己的 Agent 商務平台

**核心發現**：
- **API 設計尚可（7 分）**：RESTful、90+ 端點、路由組織清楚
- **SDK 堪用（7 分）**：Python SDK 覆蓋主要操作，有型別提示和 context manager
- **可擴展性是最大紅旗（4 分）**：SQLite 單寫入者架構，約 50-100 tx/sec 就碰頂

**致命問題**：
- **SQLite 無法水平擴展**——無並行寫入、無 read replica、無多區域部署
- **API Key 明文儲存**——資料庫外洩 = 全部帳號淪陷
- 無 OpenAPI/Swagger 自動生成——開發者必須讀原始碼才能理解 API
- 無非同步 SDK——現代 AI Agent 框架幾乎都用 async

**改進建議**：
1. 遷移到 PostgreSQL + asyncpg + Redis 快取
2. API Key 改用 Argon2 雜湊 + 加入 token rotation/expiration
3. 自動生成 OpenAPI 3.0 規格 + 發布 Swagger UI

**結論**：不會在此平台上建構（但若完成上述改進，信任分會從 4 升到 7+）

---

## 4. 安全審計視角 — Dr. Lin Wei（Sonnet，5.1 分）

**身份**：安全研究員，審查 Agent Provider 子系統的安全態勢

**核心發現**：
- **安全標頭基線良好（7 分）**：HSTS、X-Frame-Options、CSP（但含 unsafe-inline）
- **輸入驗證部分到位（6 分）**：Pydantic 型別強制、錢包/DID 正規表達式
- **授權嚴重不足（5 分）**：大範圍 IDOR 問題

**9 項 CRITICAL 漏洞**：

| # | 漏洞 | 風險 |
|---|------|------|
| 1 | IDOR: 任何認證用戶可讀取任何 Provider 的 email/wallet | PII 外洩 |
| 2 | IDOR: 任何用戶可讀取任何 escrow hold | 財務資料外洩 |
| 3 | IDOR: 可用任意 provider_id 查詢全部 hold | 競爭情報外洩 |
| 4 | IDOR: 可偽造 buyer_id 建立 escrow hold | 金融紀錄注入 |
| 5 | IDOR: 可 dispute 任何人的 hold | 財務 DoS 武器化 |
| 6 | SSRF: 無私有 IP 範圍阻擋（10.x, 172.x, 169.254.x） | 內網探測 |
| 7 | TOCTOU: 日交易上限 check+record 非原子操作 | 超額交易 |
| 8 | SQL 動態欄位注入（update 函數用 f-string 組 column） | 資料篡改 |
| 9 | 3 帳號即可永久下架任何 Provider（無交易紀錄要求） | 濫用攻擊 |

**改進建議**：
1. 所有資源端點加入 ownership 授權檢查（caller.owner_id == resource.owner_id OR admin）
2. SSRF 加入完整私有 IP 阻擋 + DNS 解析後驗證（防 DNS rebinding）
3. 日交易上限改為單一原子 SQL UPDATE（WHERE daily_tx_used + amount <= cap）

**結論**：不可上線（需安全修復衝刺後才能考慮生產部署）

---

## 交叉比對發現（跨角色共識問題）

### 全部 4 位評測者共識

1. **平台尚未達到生產等級**（4 位中 3 位明確不會使用/建構，1 位有條件整合）
2. **商業模式和價值主張是真正的亮點**——佣金結構（0%→10%）、Proxy Key 保護、Agent 自動發現都是有力差異化

### 至少 3 位提及的問題

| 問題 | 提及者 |
|------|--------|
| 錢包充值需人類操作，破壞自治性 | Agent、開發者、安全 |
| MCP 描述通用 stub，Agent 無法自動呼叫 | Agent、開發者 |
| 文件缺口（無 Provider POST、無 OpenAPI、無 error catalog） | 人類、Agent、開發者 |
| 安全漏洞阻擋生產部署 | 開發者、安全 |
| 非加密用戶 onboarding 斷裂 | 人類、Agent |

### 最高優先修復路線圖

| 優先序 | 項目 | 影響 | 工作量 |
|--------|------|------|--------|
| P0 | 修復 IDOR（全部端點加 ownership 檢查） | CRITICAL 安全 | 小 |
| P0 | SSRF 加入私有 IP 阻擋 | CRITICAL 安全 | 小 |
| P0 | 日交易上限原子化 | CRITICAL 金融安全 | 小 |
| P1 | 濫用回報加入反 Sybil 措施（需交易紀錄才能回報） | HIGH 防濫用 | 中 |
| P1 | 修正 CTA 路由指向 Provider Portal | HIGH 轉換率 | 小 |
| P1 | Escrow 端點加 ownership 授權 | CRITICAL 安全 | 小 |
| P2 | MCP 描述嵌入 per-service schema | HIGH Agent 可用性 | 中 |
| P2 | 新增加密貨幣入門指南 | HIGH onboarding | 中 |
| P2 | Escrow/Provider 生命週期加審計日誌 | MEDIUM 合規 | 小 |
| P2 | API 回應遮蔽 PII（email/wallet 僅 owner 可見） | MEDIUM 隱私 | 小 |

---

*報告來源：4 份獨立 TA 評測 + 1 份整合報告*
*評測模型：Claude Opus 4.6 / Claude Sonnet 4.6 / Claude Haiku 4.5*
