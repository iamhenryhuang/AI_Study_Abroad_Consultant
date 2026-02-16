# 資料庫結構說明

## 檔案一覽

| 檔案 | 說明 |
|------|------|
| `init_db.sql` | 資料表定義（建立 universities、requirements、deadlines） |
| `exported_data.sql` | 目前資料庫內容的匯出檔（執行匯出腳本後產生，方便檢視寫入的資料） |

## 資料表結構（init_db.sql）

### 1. universities（學校／專案）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| school_id | VARCHAR(100) UNIQUE | 學校專案代碼，如 MIT-EECS-MS |
| university | VARCHAR(255) | 學校名稱 |
| program | VARCHAR(255) | 專案名稱 |
| official_link | TEXT | 官方連結 |
| description | TEXT | 簡介（供向量檢索用） |
| created_at | TIMESTAMP | 建立時間 |

### 2. requirements（申請條件）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| university_id | INTEGER | 關聯 universities(id) |
| toefl_min_total | INTEGER | 托福最低總分 |
| toefl_required | BOOLEAN | 是否必繳托福 |
| toefl_notes | TEXT | 托福備註 |
| ielts_min_total | DECIMAL(3,1) | 雅思最低總分 |
| ielts_required | BOOLEAN | 是否必繳雅思 |
| ielts_notes | TEXT | 雅思備註 |
| gre_status | VARCHAR(50) | GRE 狀態（Required/Optional/Not Required 等） |
| gre_notes | TEXT | GRE 備註 |
| minimum_gpa | DECIMAL(3,2) | 最低 GPA |
| recommendation_letters | INTEGER | 推薦信數量 |
| interview_required | VARCHAR(100) | 是否要面試 |

### 3. deadlines（申請截止日）

| 欄位 | 型別 | 說明 |
|------|------|------|
| id | SERIAL | 主鍵 |
| university_id | INTEGER | 關聯 universities(id) |
| fall_intake | DATE | 秋季截止日 |
| spring_intake | VARCHAR(100) | 春季截止（可能為 "Not Available"） |

## 資料來源與匯出

- **寫入資料的來源**：`web_crawler/*.json`，由 `python scripts/run.py import` 匯入。
- **檢視已寫入的資料**：執行 `python scripts/run.py export` 會產生 `db/exported_data.sql`，可直接開啟該檔查看目前資料庫中的內容（INSERT 語句格式）。
