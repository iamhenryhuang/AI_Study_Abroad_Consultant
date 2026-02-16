# AI Study Abroad Consultant: 北美 CS 碩士申請輔助 RAG 系統

這是一個基於 RAG (Retrieval-Augmented Generation) 技術的留學諮詢系統，專為解決北美 CS 碩士申請資訊零散、官方要求與論壇經驗存在衝突等痛點而設計。系統整合了官方網站的「硬性指標」與 Reddit 等社群的「軟性經驗」，並提供一鍵式申請策略生成。

## 核心功能
* **多來源 RAG 檢索**：同步檢索學校官網與 Reddit 論壇資料，平衡權威性與實戰經驗。
* **混合儲存架構 (Hybrid RAG)**：
    * **PostgreSQL**：儲存 GPA、托福、Deadline 等結構化硬指標，確保篩選 100% 精準。
    * **pgvector**：儲存學校介紹、錄取心得等非結構化文字，支援語義搜索。
* **衝突資訊處理**：當官網與社群資訊不一致時，系統會進行標註並提供權重分析。
* **決策輔助系統**：使用者輸入個人背景（GPA, TOEFL, GRE, 經歷），系統自動比對數據並生成落點評估與申請策略。

## 🛠 技術棧
* **LLM**: Gemini 1.5 Flash
* **Embedding**: `BAAI/bge-m3` (支持中英跨語言檢索)
* **Database**: PostgreSQL + pgvector
* **Scraper**: Agentic Scraping (Firecrawl / LLM-based extraction)
* **Framework**: LangChain / FastAPI

## 系統流程
1. **資料層**：透過 Agentic 爬蟲抓取資料，經由 LLM 結構化後存入 PostgreSQL；非結構化文字切片 (Chunking) 後轉為向量存入 pgvector。
2. **檢索層**：結合 SQL 精準過濾與向量語義搜索。
3. **應用層**：將檢索內容與使用者 Profile 餵給 LLM，產出客製化建議。

## 資料庫與腳本（db / scripts）

- **db/**  
  - `init_db.sql`：資料表定義（universities、requirements、deadlines）。  
  - `README.md`：資料表結構說明。  
  - `exported_data.sql`：匯出產生的「目前寫入 SQL 的資料」檔案，供直接檢視。
- **scripts/**  
  - `run.py`：**統一入口**，所有資料庫操作由此執行。  
  - `db/`：內部模組（connection、setup、import_data、verify、export_data）。

## 將 web_crawler JSON 匯入 PostgreSQL
1. 複製 `.env.example` 為 `.env`，填入 `DATABASE_URL`。
2. 安裝依賴：`pip install -r requirements.txt`
3. 執行（請在專案根目錄下執行）：
   - `python scripts/run.py setup`  — 檢查連線，必要時建立 study_abroad 資料庫
   - `python scripts/run.py import` — 建表並匯入 web_crawler/*.json
   - `python scripts/run.py verify` — 檢查資料是否已寫入
   - `python scripts/run.py export` — 匯出至 db/exported_data.sql（可開啟該檔檢視寫入的資料）
