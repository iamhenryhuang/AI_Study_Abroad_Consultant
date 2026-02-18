#!/usr/bin/env python3
"""
資料庫腳本統一入口。請在專案根目錄執行：

  python scripts/run.py setup    # 檢查連線，必要時建立 study_abroad 資料庫
  python scripts/run.py import   # 建表並匯入 data/*.json
  python scripts/run.py verify   # 檢查資料是否已寫入
  python scripts/run.py export   # 匯出至 db/exported_data.sql
  python scripts/run.py init-all # 一次完成 setup + import
"""
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中，才能 import db
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db.ops import export_sql, import_json, setup_db, verify
from embed import run_embed

COMMANDS = {
    "setup": ("檢查連線並建立資料庫", setup_db),
    "import": ("建表並匯入 data/*.json", import_json),
    "verify": ("檢查資料是否已寫入", verify),
    "export": ("匯出至 db/exported_data.sql", export_sql),
    "embed": ("切片 + 向量化並寫入 document_chunks", run_embed),
    "init-all": ("建立資料庫並匯入 JSON（setup + import）", lambda: (setup_db() and import_json())),
}


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip())
        print("\n可用指令:")
        for cmd, (desc, _) in COMMANDS.items():
            print(f"  {cmd:<8}  {desc}")
        sys.exit(1)
    cmd = sys.argv[1]
    _, runner = COMMANDS[cmd]
    ok = runner()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
