# Professor Fetcher — Google Scholar 教授資料抓取模組

透過 **SerpAPI** 搜尋 Google Scholar，自動抓取教授的**研究領域**與**近兩年論文**，並格式化成與 `/data/*.json` 完全相容的格式，無縫接入現有的 chunk → embed → store pipeline。

---

## 目錄結構

```
scripts/professor_fetcher/
├── __init__.py
├── fetcher.py          # SerpAPI 呼叫邏輯（搜尋教授 ID、抓取 profile、過濾近年論文）
├── formatter.py        # 格式化為 {url: 純文字} 的 JSON
└── run_fetch.py        # CLI 入口（單一教授 / 批次模式 / 直接入庫）
```

---

## 前置步驟

### 1. 取得 SerpAPI Key

前往 [https://serpapi.com](https://serpapi.com) 註冊，每月提供 **100 次免費搜尋**。

### 2. 設定 `.env`

```dotenv
SERPAPI_KEY=your_serpapi_key_here
```

### 3. 安裝依賴

```bash
pip install requests>=2.28.0
# 或直接安裝全部
pip install -r requirements.txt
```

---

## 使用方式

所有指令請在**專案根目錄**執行。

### 單一教授（最常用）

```bash
# 基本用法（自動搜尋 author_id）
python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school "Stanford University"

# 指定已知 author_id（更精準，跳過搜尋步驟）
python -m scripts.professor_fetcher.run_fetch \
    --author-id "47730H0AAAAJ" \
    --school "Stanford University" \
    --school-id stanford

# 抓完後自動 chunk + embed + 寫入資料庫
python -m scripts.professor_fetcher.run_fetch \
    --name "Fei-Fei Li" --school "Stanford University" --embed
```

### 批次模式（多位教授）

建立設定檔（例如 `professors.json`）：

```json
[
  {"name": "Andrew Ng",    "school": "Stanford University", "school_id": "stanford"},
  {"name": "Tom Mitchell", "school": "Carnegie Mellon University", "school_id": "cmu"},
  {
    "name": "Yoshua Bengio",
    "school": "Université de Montréal",
    "school_id": "umontreal",
    "author_id": "34ai450AAAAJ"
  }
]
```

```bash
# 批次抓取，儲存為各學校的 JSON
python -m scripts.professor_fetcher.run_fetch --config my_professors.json

# 批次抓取 + 直接入庫
python -m scripts.professor_fetcher.run_fetch --config my_professors.json --embed
```

### 完整參數說明

| 參數 | 說明 | 預設值 |
|------|------|--------|
| `--name` | 教授全名（單一模式） | — |
| `--school` | 學校名稱 | — |
| `--school-id` | 學校 ID（stanford/cmu/mit...） | 自動推斷 |
| `--author-id` | Google Scholar author_id（若已知） | — |
| `--config` | 批次設定檔路徑（JSON） | — |
| `--cutoff-year` | 論文最早年份 | 當年 - 2 |
| `--max-papers` | 每位教授最多抓幾篇近年論文 | 20 |
| `--delay` | API 呼叫間隔秒數 | 1.0 |
| `--embed` | 完成後自動 chunk + embed + 入庫 | false |

---

## 輸出格式

與 `/data/stanford.json`、`/data/cmu.json` 完全相同：

```json
{
  "https://scholar.google.com/citations?user=47730H0AAAAJ&hl=en": 
    "Professor Profile: Andrew Ng Affiliation: Stanford University Research Interests: Machine Learning, Deep Learning, AI Total Citations: 500000 H-Index: 85 Recent Publications (since 2024 — 3 papers): [2024] LLM Alignment for Education ...",

  "https://scholar.google.com/citations?view_op=view_citation&user=47730H0AAAAJ&citation_for_view=...:hl=en":
    "Research Paper by Professor Andrew Ng Title: LLM Alignment for Education Authors: Andrew Ng, John Smith Published in: ICML 2024 Year: 2024 Citations: 42 ..."
}
```

**每位教授產生的 entries：**
- **1 個 profile entry** — 包含：姓名、機構、研究興趣、引用統計、近年論文概覽、全部論文列表
- **N 個論文 entries** — 每篇近年論文各一個，包含：標題、作者、期刊/會議、年份、引用數

---

## 輸出檔案位置

結果儲存在 `/data/{school_id}_professors.json`，**自動合併**（不覆蓋既有資料）：

```
data/
├── stanford.json          # 原有的學校申請資訊
├── stanford_professors.json   ← 新增：Stanford 教授 Google Scholar 資料
├── cmu.json
├── cmu_professors.json        ← 新增：CMU 教授資料
└── ...
```

---

## 與 Embedding Pipeline 整合

### 方式一：使用 `--embed` 旗標（最方便）

```bash
python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school Stanford --embed
```

### 方式二：手動執行 pipeline

```bash
# 抓取並儲存 JSON
python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school Stanford

# 對所有 JSON 重新執行 pipeline（包含新增的教授資料）
python -m scripts.embedder.pipeline
```

### 方式三：只對教授 JSON 執行

```bash
# pipeline.py 的 run_pipeline() 接受 data_dirname 參數
# 可以傳入整個 data/ 目錄（一起處理）
python -m scripts.embedder.pipeline
```

---

## Chunker 支援的新頁面類型

本模組在 `chunker.py` 中新增了兩個 page_type：

| page_type | chunk_size | 說明 |
|-----------|-----------|------|
| `professor_profile` | 1800 字元 | 教授 profile 頁面（較大，保留完整個人資訊） |
| `professor_paper` | 1000 字元 | 單篇論文 citation 頁面（較短） |

`infer_page_type()` 函數也已更新，可自動從 `scholar.google.com` URL 推斷類型。

---

## 如何找到 Author ID

1. 前往 [Google Scholar](https://scholar.google.com)
2. 搜尋教授姓名
3. 點入教授 profile
4. 從 URL 取得：`https://scholar.google.com/citations?user=**{author_id}**`

或讓系統自動搜尋（使用 `--name` + `--school` 參數）。
