#!/usr/bin/env python3
"""
資料庫腳本統一入口。請在專案根目錄執行：

  python scripts/run.py setup   # 檢查連線，必要時建立 study_abroad 資料庫
  python scripts/run.py import  # 建表並匯入 web_crawler/*.json
  python scripts/run.py verify  # 檢查資料是否已寫入
  python scripts/run.py export  # 匯出至 db/exported_data.sql
"""
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中，才能 import db
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db.setup import run as run_setup
from db.import_data import run as run_import
from db.verify import run as run_verify
from db.export_data import run as run_export

COMMANDS = {
    "setup": ("檢查連線並建立資料庫", run_setup),
    "import": ("建表並匯入 web_crawler JSON", run_import),
    "verify": ("檢查資料是否已寫入", run_verify),
    "export": ("匯出至 db/exported_data.sql", run_export),
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
