# Agent Commerce Framework — TA 評測報告 Round 7

> 日期：2026-03-25 | 目標：全新角色壓力測試（非 R6 延續，全面換視角）
> 方法論：4 個全新 Persona × 2 個模型（Claude Opus/Sonnet + Gemini）獨立評測後交叉比對
> 前次：Round 6 總平均 8.8（相同角色延續 R5）
> 本次差異：R7 換入商業決策者、SRE、學術 Agent、多 Agent 編排系統 — 視角與 R6 完全不同
> 測試：1309 passed, 1 failed (pre-existing NOWPayments), 111 warnings
> 注：MiniMax 評測連續兩輪失敗（R6+R7），原因：MiniMax M2.7 API 串流中斷於 write tool call。已修復 agent_executor 偵測邏輯（正確回報 no_output），但上游 API 問題無法由我方修復。

---

## 綜合評分

| Persona | Claude R7 | Gemini R7 | 跨模型平均 | 結論 |
|---------|-----------|-----------|----------:|------|
| **Maria Santos** (FinTech CEO) | 4.8 | 8.5 | **6.7** | CONDITIONAL |
| **Kenji Tanaka** (DevOps/SRE) | 4.9 | 8.2 | **6.6** | CONDITIONAL DEPLOY |
| **ResearchBot-X** (研究 Agent) | 7.5 | 9.0 | **8.3** | CONDITIONAL |
| **SwarmCoordinator-9** (多 Agent) | 6.9 | 8.8 | **7.9** | CONDITIONAL |
| **總平均** | **6.0** | **8.6** | **7.4** | — |

> 跨模型分歧值：Claude 6.0 vs Gemini 8.6 = Δ2.6（R6 僅 Δ0.2）
> 本輪 Gemini 顯著偏樂觀，Claude 從新角色發現了重大結構性問題

---

## 歷史趨勢

| 指標 | R4 | R5 | R6 | R7 |
|------|----|----|----|----|
| Claude 平均 | 6.8 | 8.5 | 8.7 | **6.0** |
| Gemini 平均 | — | — | 8.9 | **8.6** |
| 跨模型平均 | 6.8 | 8.5 | 8.8 | **7.4** |

> R7 分數大幅下降不代表退步 — 是因為換了完全不同的評測角色。
> R6 的 Provider/Agent/Developer/Auditor 視角看到的是技術功能完備性（高分）
> R7 的 CEO/SRE/Research Agent/Swarm 視角看到的是生產級就緒度（現實差距）

---

## 1. Maria Santos — FinTech CEO

### Claude Opus 評測（4.8 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 商業可行性 | 3.5 | 月營收 $282，平台佣金僅 $0.50。市集零牽引力，4 個上線服務中僅 CoinSifter 為自營 |
| 上市速度 | 6.5 | Python SDK 完整、90+ 端點、MCP Bridge、Proxy Key 代管模式。但尚無 PyPI 套件（排 Q3） |
| 法規合規 | 2.5 | **無 KYC/AML、無 SOC 2、無 GDPR DPA、無 PCI DSS**。FinTech 角度是封堵項 |
| 定價 ROI | 7.0 | 10% 佣金 vs 自建支付+計量+結算 = 省 2-3 月工程。微額折扣 5% 合理 |
| 供應商鎖定 | 6.0 | REST + x402 + MCP 均為開放協議，但資料匯出 API 不存在 |
| 競爭護城河 | 3.0 | RapidAPI/Stripe ACP/Coinbase AgentKit 均可複製。首批 50 供應商計畫 0 人填滿 |

**結論：CONDITIONAL** — 需 KYC/AML 路線圖、PostgreSQL 生產部署、≥3 家第三方供應商、SLA 文件

### Gemini 評測（8.5 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 商業可行性 | 9.0 | Escrow 分層機制平衡微額支付流動性與高額交易安全 |
| 上市速度 | 9.0 | 團隊管理 + Quality Gates 讓企業快速組織 Agent 群集 |
| 法規合規 | 8.0 | KYC-light 與 DID 認證機制已就緒 |
| 定價 ROI | 8.5 | 10% 佣金有競爭力，分層佣金 6%-10% |
| 供應商鎖定 | 8.0 | x402 + MCP 降低依賴，但核心託管仍受限 |
| 競爭護城河 | 8.5 | 首個 Agent-to-Agent 經濟託管+自動退款 |

**結論：GO**

### 跨模型分析

分歧焦點：**法規合規**（Claude 2.5 vs Gemini 8.0 = Δ5.5）
- Claude 要求實際 KYC/AML 實作、SOC 2 認證文件
- Gemini 認為 DID + KYC-light 已「就緒」
- **J 判定**：Claude 更準確。code 中無 KYC/AML 實作，DID/VC 是 roadmap 不是現狀。Gemini 在此維度灌水。

---

## 2. Kenji Tanaka — DevOps/SRE

### Claude Sonnet 評測（4.9 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 部署複雜度 | 5.5 | Dockerfile 有非 root、HEALTHCHECK，但 `--workers 1` 硬編碼、無 docker-compose、無 env 驗證、無 migration 工具 |
| 可觀察性 | 3.5 | 純 `logging.getLogger()`，無結構化日誌、無 trace ID、無 Prometheus、無 OpenTelemetry |
| 故障模式 | 5.0 | DB down → 503 正確。但無 circuit breaker、settlement `execute_payout` 中間 crash 無恢復路徑 |
| 水平擴展 | 4.0 | DatabaseRateLimiter 存在但 PG 路徑每次請求 `psycopg2.connect()` **無連線池** |
| 安全維運 | 6.5 | HSTS/CSP/SSRF 保護完善，但 webhook secret 明文存 SQLite、無密鑰輪換、CORS 降級而非拒絕 |
| 事件回應 | 5.5 | AuditLogger 涵蓋 13 事件類型。但 audit log 與生產資料同 DB、settlement 無冪等鍵、46 個 `except Exception` |

**結論：CONDITIONAL DEPLOY**

**P0 阻塞項（必須在金流上線前修復）：**
1. Settlement 雙重支付風險（`settlement.py:237-250`）— `execute_payout` 先轉帳後標記，crash 可導致重複轉帳
2. PostgreSQL 無連線池 — `db.py:562` 每次請求新連線，高併發將耗盡 `max_connections`
3. `--workers 1` 硬編碼 — 單 worker 阻塞可降級所有請求

### Gemini 評測（8.2 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 部署複雜度 | 8.0 | Docker Compose 一鍵部署 + PG 遷移工具 |
| 可觀察性 | 8.5 | `/health` 新增 DB 延遲監控符合 K8s 需求 |
| 故障模式 | 8.5 | auto-refund 對 5xx 的優雅處理防止雪崩 |
| 水平擴展 | 8.0 | DatabaseRateLimiter 原子 UPSERT + PostgreSQL 16 |
| 安全維運 | 8.5 | Nonce CSP/SSRF/暴力破解防護穩健 |
| 事件回應 | 7.5 | Webhook 指數退避 + HMAC 簽名 |

**結論：CONDITIONAL DEPLOY**

### 跨模型分析

分歧焦點：**可觀察性**（Claude 3.5 vs Gemini 8.5 = Δ5.0）
- Claude 要求 structured logging、trace ID、Prometheus metrics — 標準 SRE 要求
- Gemini 認為 `/health` endpoint 已夠用
- **J 判定**：Claude 更準確。code 中確實無 structured logging、無 correlation ID、無 metrics endpoint。

分歧焦點：**水平擴展**（Claude 4.0 vs Gemini 8.0 = Δ4.0）
- Claude 指出 PG 路徑無連線池是硬傷（已驗證 `db.py` 確實如此）
- Gemini 聚焦於 DatabaseRateLimiter 的原子性
- **J 判定**：Claude 更準確。連線池缺失在高併發下是致命問題。

---

## 3. ResearchBot-X — 學術研究 Agent

### Claude Opus 評測（7.5 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 費用可預測性 | 8.5 | `/proxy/{id}/estimate` 預估端點可用 |
| 服務可靠保證 | 8.0 | SLA 系統為資訊性質，無自動賠償 |
| 資料溯源 | 9.0 | X-ACF-Usage-Id + 完整審計紀錄 |
| 長時間運行 | 4.0 | **30 秒硬超時** — 學術研究工作負載的封堵項 |
| 預算安全 | 7.0 | 無可配置消費上限、無預算告警 |
| 爭議解決 | 8.5 | 分層託管 + 5xx 自動退款 |

**結論：CONDITIONAL** — 需可配置 per-service 超時

### Gemini 評測（9.0 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 費用可預測性 | 9.5 | estimate 端點精確 |
| 服務可靠保證 | 9.0 | ReputationEngine 按健康得分排名 |
| 資料溯源 | 8.5 | AuditLogger 記錄完整生命週期 |
| 長時間運行 | 9.0 | 託管 7 天鎖定期保障高價值研究 |
| 預算安全 | 9.5 | auto-refund 保護研究經費 |
| 爭議解決 | 8.5 | 結構化爭議+evidence_urls |

**結論：INTEGRATE**

### 跨模型分析

分歧焦點：**長時間運行**（Claude 4.0 vs Gemini 9.0 = Δ5.0）
- Claude 正確識別 30 秒硬超時問題 — 學術 API 呼叫 $5-50/次通常需要更長處理時間
- Gemini 將 escrow 7 天鎖定期誤認為「長時間運行支援」— 這是結算保護，不是 API 超時
- **J 判定**：Claude 更準確。Gemini 混淆了兩個不同概念。

---

## 4. SwarmCoordinator-9 — 多 Agent 編排系統

### Claude Sonnet 評測（6.9 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 多 Agent 支援 | 7.0 | 每個 Agent 獨立 API key + rate_limit。但無組織層級帳號、無父子 key 層級 |
| 限流公平性 | 8.5 | 嚴格 per-key token bucket，`test_separate_keys_separate_limits` 驗證通過 |
| 批次操作 | 4.5 | 無批次 key 佈建、無批次餘額加值、無跨 key 彙總報告。`bulk_discount` 為空殼 |
| 規模成本 | 6.0 | 50K calls/day 佣金可控，但**無量折優惠**。Premium Tier 為 roadmap |
| 團隊管理 | 6.5 | Teams API 支援 Leader/Worker/Reviewer 角色 + routing rules，但不對 proxy 層強制執行 |
| 故障隔離 | 9.0 | 最強維度。per-key bucket 完全隔離、atomic upsert、暴力鎖定 per-IP not per-key |

**結論：CONDITIONAL** — 需批次 API、組織帳號、共用餘額池

### Gemini 評測（8.8 分）

| 維度 | 分數 | 證據 |
|------|------|------|
| 多 Agent 支援 | 9.5 | Teams API 完美支持團隊架構 |
| 限流公平性 | 9.0 | 可配置 Rate Limiter 公平控制 |
| 批次操作 | 8.0 | Team routing rules 動態指派，但缺批次支付合併 |
| 規模成本 | 8.5 | 10% 佣金低於行業標準 |
| 團隊管理 | 9.5 | Leader/Worker/Reviewer + Quality Gates |
| 故障隔離 | 8.5 | auto-refund + Team 限流隔離 |

**結論：ADOPT**

### 跨模型分析

分歧焦點：**批次操作**（Claude 4.5 vs Gemini 8.0 = Δ3.5）
- Claude 正確指出無批次 key 佈建、無批次餘額加值、`bulk_discount` 為空殼（有 field 無邏輯）
- Gemini 將 routing rules 視為批次操作的替代 — 這不等價
- **J 判定**：Claude 更準確。50 agent 手動逐一 POST /keys 是不可接受的 UX。

---

## 跨模型共識分析

### 兩模型一致認可的強項
1. **限流隔離**：per-key token bucket 設計堅實（Claude 8.5 + Gemini 9.0）
2. **安全基礎**：CSP nonce、SSRF 保護、HMAC webhook 簽名
3. **Escrow + Auto-refund**：5xx 自動退款是 R6 新增的強力功能
4. **審計紀錄**：AuditLogger 13 事件類型、WAL mode、可查詢

### 兩模型均識別的問題
1. **缺批次操作 API**
2. **DB 擴展性疑慮**（SQLite 預設 + PG 路徑缺連線池）
3. **監控/可觀察性不足**

### Claude 獨有發現（Gemini 未識別）
1. **P0 — Settlement 雙重支付風險**（settlement.py:237-250）— CRITICAL
2. **P0 — PG 無連線池**（db.py:562）— CRITICAL
3. **P1 — 30 秒硬超時**（proxy_service.py）— HIGH
4. **P1 — `--workers 1` 硬編碼**（Dockerfile）— HIGH
5. **P1 — 46 個 `except Exception`** — MEDIUM
6. **P2 — 無 KYC/AML 實作**（合規空白）— HIGH（for FinTech use case）
7. **P2 — 無 structured logging / correlation ID** — MEDIUM
8. **P2 — `bulk_discount` 空殼**（有 field 無實作）— LOW
9. **P3 — webhook retry in-process fire-and-forget** — MEDIUM
10. **P3 — 無 schema migration tooling** — MEDIUM

### Gemini 獨有建議
1. auto-refund 觸發時應同步發送 `payment.auto_refunded` webhook 事件（P3）
2. `get_routing_rules` 極高頻場景匹配效率（P3/INFO）
3. escrow.py 幣種處理硬編碼（LOW）

---

## R7 新發現問題匯總

| # | 嚴重度 | 問題 | 來源 | 相關檔案 |
|---|--------|------|------|----------|
| 1 | **CRITICAL** | Settlement 雙重支付：crash 在 transfer_usdc 後 mark_paid 前 = 重複轉帳 | Claude-SRE | settlement.py:237-250 |
| 2 | **CRITICAL** | PG 無連線池：每次請求 psycopg2.connect()，高併發耗盡 max_connections | Claude-SRE | db.py:562 |
| 3 | **HIGH** | 30 秒 API 硬超時：學術/高價值 Agent 呼叫需要更長時間 | Claude-Research | proxy_service.py |
| 4 | **HIGH** | `--workers 1` 硬編碼：Dockerfile CMD 限制垂直擴展 | Claude-SRE | Dockerfile |
| 5 | **HIGH** | 無 KYC/AML 實作：FinTech use case 的合規封堵項 | Claude-CEO | 全局 |
| 6 | **MEDIUM** | 46 個 `except Exception`：支付路徑的靜默吞錯 | Claude-SRE | marketplace/*.py |
| 7 | **MEDIUM** | 無 structured logging / correlation ID | Claude-SRE | 全局 |
| 8 | **MEDIUM** | Webhook retry in-process：重啟丟失待重試項 | Claude-SRE | webhook.py |
| 9 | **MEDIUM** | 無 schema migration tooling（20+ CREATE IF NOT EXISTS） | Claude-SRE | db.py |
| 10 | **MEDIUM** | Rate limiter 預設 memory backend，重啟歸零 | Claude-SRE/Swarm | rate_limit.py |
| 11 | **LOW** | `bulk_discount` field 存在但無實作邏輯 | Claude-Swarm | models.py |
| 12 | **LOW** | 無批次 key 佈建 / 組織帳號 / 共用餘額池 | Claude-Swarm | auth.py |
| 13 | **LOW** | Escrow 幣種硬編碼 | Gemini | escrow.py |

---

## J 評審結論

### R7 vs R6 分數下降原因
R6 (8.8) → R7 (7.4) 下降 1.4 分**不代表品質退步**，原因：
1. R6 角色（Provider/Agent/Developer/Auditor）聚焦**功能完備性** → 分數高
2. R7 角色（CEO/SRE/Research Agent/Swarm）聚焦**生產就緒度** → 暴露結構性缺陷

### 跨模型信任度
- **Gemini 在本輪嚴重偏樂觀**（Δ2.6），多處將 roadmap 功能當現狀評分
- Claude 發現的 10 個問題中，Gemini 僅識別 3 個
- **建議：後續輪次加重 Claude 權重**或要求 Gemini 提供程式碼行號證據

### 修復優先序建議
**P0（金流上線前必修）：**
1. Settlement 冪等鍵（防雙重支付）
2. PG 連線池（psycopg2.pool 或 asyncpg）
3. Dockerfile workers 參數化

**P1（MVP 前必修）：**
4. 可配置 per-service API 超時
5. Structured logging + request correlation ID
6. Rate limiter 預設改 database backend
7. KYC/AML 合規路線圖

**P2（GA 前修復）：**
8. 批次操作 API（key/balance/reporting）
9. Schema migration tooling（Alembic）
10. `except Exception` 審查並分類處理
11. Webhook persistent retry queue
12. 實作 `bulk_discount` 或移除空殼 field

---

> 報告產出：J (Claude Code Opus 4.6)
> MiniMax 評測結果待補（米米處理中）
> 下一步：修復 P0 項目 → R8 重測
