# scripts 目錄

所有資料庫相關操作都透過**單一入口**執行，不再散落多個腳本。

## 使用方式（請在專案根目錄執行）

```bash
python scripts/run.py <指令>
```

| 指令 | 說明 |
|------|------|
| `setup` | 檢查 PostgreSQL 連線，若無 `study_abroad` 資料庫則建立 |
| `import` | 依 `db/init_db.sql` 建表，並將 `web_crawler/*.json` 匯入 |
| `verify` | 檢查 universities / requirements / deadlines 是否已有資料 |
| `export` | 將目前資料庫內容匯出成 `db/exported_data.sql` |

## 目錄結構

```
scripts/
  run.py          # 唯一對外入口
  README.md       # 本說明
  db/             # 內部模組（不需直接執行）
    __init__.py
    connection.py # 共用連線與 ROOT
    setup.py
    import_data.py
    verify.py
    export_data.py
```
