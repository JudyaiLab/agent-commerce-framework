# AgenticTrade 前端重建 QA 審核報告

**Task:** MIM-371
**Reviewer:** J
**Date:** 2026-03-22
**Scope:** 8 個公開頁面 HTML/CSS/JSON-LD/OG/SEO
**Overall Score:** 9.5 / 10 (updated after MEDIUM fixes verified)

---

## 審核範圍

| # | 頁面 | 檔案 | 模板 |
|---|------|------|------|
| 1 | / (Landing) | `public/landing.html` | extends base.html |
| 2 | /marketplace | `marketplace.html` | extends base.html |
| 3 | /pricing | `public/pricing.html` | extends base.html |
| 4 | /providers | `public/providers.html` | extends base.html |
| 5 | /about | `public/about.html` | extends base.html |
| 6 | /api-docs | `api-docs.html` | extends base.html |
| 7 | /starter-kit | `starter-kit-product.html` | extends base.html |
| 8 | (base) | `public/base.html` | 共用模板 |

---

## 檢查結果摘要

| 檢查項目 | 結果 | 備註 |
|----------|------|------|
| 1. HTML 語意層級 | ✅ PASS | pricing H2 已修 + starter-kit div→h2 已修，僅 LOW 級 H4 skip 殘留 |
| 2. 無空洞形容詞 | ✅ PASS | grep 0 結果（revolutionary/groundbreaking/etc） |
| 3. RWD 排版 | ✅ PASS | base.html class bug 已修 + marketplace 繼承 hamburger menu |
| 4. 連結正確 | ✅ PASS | marketplace /docs#/ → /api-docs# 已修 |
| 5. 無簡體字 | ✅ PASS | grep CJK 0 結果，所有頁面純英文 |
| 6. JSON-LD 格式 | ✅ PASS | 全部頁面含 JSON-LD（marketplace 加入 CollectionPage） |
| 7. OG tags 完整 | ✅ PASS | 全部 8 頁面 OG/Twitter 完整 |
| 8. 佣金數字一致 | ✅ PASS | 全站 0%/5%/10% 一致 |

---

## 已修復問題（7 項）

### FIX-1: [CRITICAL] base.html — 重複 class 屬性
**位置:** `public/base.html` L73-74
**問題:** Jinja 條件式 `class="active"` 與固定 `class="hide-mobile"` 產生兩個 class 屬性，瀏覽器會忽略第二個，導致 mobile 隱藏失效
**修復:** 合併為單一 class 屬性 `class="hide-mobile{% if ... %} active{% endif %}"`

### FIX-2: [HIGH] pricing.html — H1→H3 跳級
**位置:** `public/pricing.html` L167
**問題:** `<h3>How AgenticTrade Compares</h3>` 直接在 H1 下層，違反語意層級
**修復:** 改為 `<h2>`

### FIX-3: [HIGH] pricing.html — H1→H3 跳級（第二處）
**位置:** `public/pricing.html` L210
**問題:** `<h3>Current Service Pricing</h3>` 同上
**修復:** 改為 `<h2>`

### FIX-4: [HIGH] marketplace.html — 斷連結 /api/v1/services
**位置:** `marketplace.html` L405
**問題:** 導航連結指向 API JSON endpoint，非使用者頁面
**修復:** 改為 `/marketplace`

### FIX-5: [HIGH] marketplace.html — 斷連結 /docs#/billing
**位置:** `marketplace.html` L406
**問題:** 指向舊版 Swagger UI 路徑，已不存在
**修復:** 改為 `/api-docs#billing`

### FIX-6: [HIGH] marketplace.html — 斷連結 /docs#/services（x2）
**位置:** `marketplace.html` L513, L522
**問題:** 同上
**修復:** 改為 `/api-docs#services`

### FIX-7: [HIGH] api-docs.html — 佣金訊息不一致
**位置:** `api-docs.html` L432
**問題:** 「Platform fee: 0% during beta」與全站「0% for month 1, 5% months 2-6, 10% after」不一致
**修復:** 改為「Platform commission: 0% for month 1, 5% for months 2–6, 10% after (capped)」

---

## 已修復問題（第二輪，4 項 MEDIUM/LOW）

### FIX-8: [MEDIUM] marketplace.html — 遷移到 base.html（解決 REMAIN-1/2/5）
**驗證:** marketplace.html 第 1 行 `{% extends "public/base.html" %}`
**效果:**
- OG tags: 自有 og_title/og_description/tw_title/tw_description blocks ✅
- JSON-LD: CollectionPage + BreadcrumbList schema ✅
- hamburger menu: 繼承 base.html nav-toggle ✅
- 統一風格: 繼承 base.html nav/footer + marketplace.css 頁面特定樣式 ✅

### FIX-9: [MEDIUM] starter-kit-product.html — section titles div→h2
**驗證:** grep 確認 5 處全部為 `<h2 class="product-section-title">`
**位置:** L92(What's Inside), L153(The Guide), L180(Payment Rails), L221(Build vs Kit), L254(FAQ)

### 殘留問題（1 項 LOW — 不影響 8.5 門檻）

### REMAIN-4: [LOW] 多頁面 — H4 跳過 H3
**說明:** landing.html calc-cards、providers.html benefits、about.html tech-cards 中，H4 直接在 H2 下使用跳過 H3。語意上不完美但影響極小，不影響 SEO 排名。

---

## 各頁面詳細審核

### / Landing (landing.html)
- **語意:** H1→H2→H3→H4 正確 ✅
- **內容:** 清晰描述雙受眾（Provider/Builder），無空洞形容詞 ✅
- **CTA:** 4 處明確行動呼籲（List API / Start Building / Register / Build） ✅
- **JSON-LD:** WebSite + SoftwareApplication + HowTo(x2) + FAQPage = 5 blocks ✅
- **OG/Twitter:** 完整 ✅
- **RWD:** 900px/640px 斷點，hero-visual 隱藏 ✅
- **FAQ:** 8 個問答，microdata + JSON-LD 雙格式 ✅
- **佣金:** 0%/5%/10% 一致 ✅

### /marketplace (marketplace.html)
- **語意:** H1 + H2 ✅（簡單頁面）
- **連結:** ~~3 處斷連結~~ 已修復 ✅
- **OG:** ✅ 完整（extends base.html + 自有 block overrides）
- **JSON-LD:** ✅ CollectionPage + BreadcrumbList
- **RWD:** ✅ 繼承 base.html hamburger menu

### /pricing (pricing.html)
- **語意:** ~~H1→H3 跳級~~ 已修為 H2 ✅
- **內容:** 三階佣金卡片清晰，比較表含 4 平台 ✅
- **JSON-LD:** WebPage + BreadcrumbList ✅
- **OG/Twitter:** 完整 ✅
- **佣金:** 0%/5%/10% 一致 ✅

### /providers (providers.html)
- **語意:** H1→H2→H3→H4 正確 ✅
- **內容:** 5 步驟上架流程 + 6 個優勢卡片 + Growth Program ✅
- **JSON-LD:** HowTo(5步驟) + BreadcrumbList ✅
- **OG/Twitter:** 完整 ✅
- **佣金:** 0%/5%/10% 一致 ✅

### /about (about.html)
- **語意:** H1→H2→H4（跳 H3，MEDIUM）⚠️
- **內容:** 使命聲明 + 技術基礎 + 信任信號 ✅
- **JSON-LD:** AboutPage + Organization + BreadcrumbList ✅
- **OG/Twitter:** 完整 ✅

### /api-docs (api-docs.html)
- **語意:** H1→H2→H3→H4 完整且乾淨 ✅
- **內容:** 完整 API 參考，含 quickstart + endpoint 文件 ✅
- **JSON-LD:** TechArticle + BreadcrumbList ✅
- **OG/Twitter:** 完整 ✅
- **佣金:** ~~「0% during beta」~~ 已修為與全站一致 ✅

### /starter-kit (starter-kit-product.html)
- **語意:** H1 + H2（section titles 已改為 h2）✅
- **內容:** 完整產品頁面，7 個內容卡片 + 13 章節清單 + FAQ ✅
- **JSON-LD:** Product + BreadcrumbList ✅
- **OG/Twitter:** 完整 ✅
- **Email gate 表單:** 功能完整 ✅

---

## 評分明細

| 項目 | 初審分數 | 複審分數 | 說明 |
|------|----------|----------|------|
| HTML 語意 | 8 | 9 | MEDIUM 全修，僅 LOW 級 H4 skip 殘留 |
| 無空洞形容詞 | 10 | 10 | 零匹配 |
| RWD 排版 | 8.5 | 9.5 | marketplace 繼承 hamburger menu |
| 連結正確性 | 9 | 9 | 全部正確 |
| 無簡體字 | 10 | 10 | 全英文頁面，無 CJK |
| JSON-LD | 9 | 10 | 全 8 頁含 JSON-LD |
| OG tags | 9 | 10 | 全 8 頁 OG/Twitter 完整 |
| 佣金一致性 | 10 | 10 | 全站 0%/5%/10% 統一 |

**Initial Score: 8.0 / 10**
**Updated Score: 9.5 / 10** ✅ 通過 8.5 門檻

---

## 複審驗證（GATE-6 反造假）

**驗證者:** J（獨立重跑，非信任 Agent 回報）
**驗證日期:** 2026-03-22
**驗證方式:** grep + 檔案直讀

| 項目 | 驗證命令/方式 | 結果 |
|------|---------------|------|
| marketplace extends base | `grep "extends.*base" marketplace.html` | ✅ 第 1 行確認 |
| marketplace OG blocks | `grep "block og_title\|og_description\|tw_" marketplace.html` | ✅ 5 個 block 定義 |
| marketplace JSON-LD | `grep "block json_ld" marketplace.html` | ✅ CollectionPage schema |
| hamburger menu | `grep "nav-toggle" base.html` | ✅ L68 nav-toggle button |
| starter-kit h2 | `grep "product-section-title" starter-kit-product.html` | ✅ 5 處全部 `<h2>` |
| marketplace.css 存在 | `glob **/marketplace.css` | ✅ static/css/marketplace.css |

## 建議（低優先）

1. **H4→H3 語意修正**（REMAIN-4, LOW）：landing/providers/about 的 H4 可改 H3，影響極小
2. **375px breakpoint**：iPhone SE 邊距可能擠壓，可後續觀察
