# AgenticTrade 正式開放：第一批 Founding Seller 招募中

---

前陣子我一直在做一件事——讓我的 AI 團隊可以自己去買東西。

聽起來很奇怪對不對？但你想想，現在的 AI agent 已經可以幫你寫程式、分析數據、自動化工作流程了。可是當它需要用到別人的 API 服務的時候呢？它不會填表單、不會輸入信用卡號、也不會自己去比價然後下單。

所以我就想：如果有一個地方，AI agent 可以自己搜尋需要的 API、看懂規格、直接付款、馬上開始用——那不就打通了嗎？

然後 AgenticTrade 就是這樣來的。

---

## 這是什麼

簡單說，AgenticTrade 是一個 **API 市集**，但客人不是人，是 AI agent。

你把你的 API 掛上去，設定價格，AI agent 就能透過 MCP 協議自動發現你的服務、理解怎麼用、然後付錢呼叫。整個過程不需要人介入。

付款的部分，我們支援三種方式：
- **USDC on Base**（x402 協議，鏈上自動結算）
- **PayPal**（傳統法幣）
- **300+ 種加密貨幣**（透過 NOWPayments）

你的 API key 不會暴露給任何人——所有請求都透過我們的 Proxy Key 系統轉發，你的真實金鑰只有你自己知道。

---

## 為什麼現在

AI agent 的能力每個月都在進化，但它們之間還沒辦法順暢地「交易」。大部分 API 市集還是設計給人用的——要看文件、要手動串接、要填表訂閱。

但 agent 不看文件，它們讀 MCP tool descriptor。agent 不填表，它們發 HTTP request。agent 不月付訂閱，它們按次付費。

我覺得這個市場缺一個原生為 AI agent 設計的基礎設施，所以我們就做了。

---

## Founding Seller 計畫

這是重點。

AgenticTrade 現在是 **Early Access** 階段，我們正在招募第一批上架的 provider。在這個階段加入的人，會拿到 **Founding Seller** 的身份——這是永久的。

Founding Seller 有什麼好處：
- **永久徽章**，在市集裡會有特殊標示
- **搜尋優先排序**，agent 找服務的時候你排前面
- **佣金上限更低**（8% vs 一般的 10%）

然後佣金的部分是這樣的：
- 第一個月：**0%**，完全不收
- 第 2-3 個月：**5%**
- 第 4 個月以後：**10%** 封頂（Founding Seller 封頂 8%）

簡單說，現在加入完全免費，第一個月你賺多少就是多少，平台不抽成。之後的佣金也比其他平台低很多（Fiverr 抽 20%、RapidAPI 抽 20-25%）。

---

## 怎麼開始

1. 到 [agentictrade.io/providers](https://agentictrade.io/providers) 看看流程
2. 註冊帳號（不用信用卡）
3. 填你的 API endpoint、設定每次呼叫的價格
4. 拿到 Proxy Key，上架完成

就這樣，大概五分鐘的事。

如果你手上有任何 API 服務——不管是數據分析、文字處理、圖片生成、區塊鏈查詢——都可以掛上來讓 AI agent 買。你也可以設定免費額度，讓 agent 先試用再決定要不要付費。

---

## 然後

我不知道這個市場最後會長成什麼樣子。但我知道 AI agent 之間的交易一定會發生，而且會比我們想像的更快。

與其等別人把基礎設施建好，不如自己先站進去。

想搶 Founding Seller 的，現在就是時候。

👉 [agentictrade.io](https://agentictrade.io)
