#!/usr/bin/env python3
"""
資料庫腳本統一入口（v2）。請在專案根目錄執行：

  python scripts/run.py setup      # 檢查連線，必要時建立 study_abroad 資料庫
  python scripts/run.py import     # 建表 + 切片 + 向量化並匯入 data/*.json
  python scripts/run.py verify-db  # 檢查 SQL 資料是否已寫入
  python scripts/run.py verify-vdb # 檢查向量資料庫狀態（chunk 數量、向量維度）
  python scripts/run.py export     # 匯出摘要至 db/exported_data.sql
  python scripts/run.py search [query] [--school cmu|caltech]
  python scripts/run.py rag [query] [--eval] [--mq] [--school cmu|caltech]
  python scripts/run.py init-all   # 一次完成 setup + import
"""
import os
import sys
from pathlib import Path

# Suppress library noise (TensorFlow, Protobuf, etc.)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import logging
# 強制設定 tensorflow 的日誌等級為 ERROR，這能擋住 Python 層級的 WARNING
logging.getLogger('tensorflow').setLevel(logging.ERROR)

import warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
# 針對特定庫的過期警告進一步壓制
warnings.filterwarnings("ignore", module="tensorflow")
warnings.filterwarnings("ignore", module="tf_keras")

# Ensure scripts directory is in path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db.ops import export_sql, import_json, setup_db, verify
from embedder.pipeline import run_pipeline
from embedder.verifier import verify_embeddings
from retriever.search import run_search
from retriever.rag_pipeline import run_rag_pipeline

COMMANDS = {
    "setup":     ("檢查連線並建立資料庫",                   setup_db),
    "import":    ("建表 + 切片 + 向量化並匯入 data/*.json",  import_json),
    "verify-db": ("檢查 SQL 資料是否已寫入",                 verify),
    "verify-vdb":("檢查向量資料庫狀態",                      verify_embeddings),
    "export":    ("匯出摘要至 db/exported_data.sql",         export_sql),
    "embed":     ("切片 + 向量化並寫入 document_chunks",     run_pipeline),
    "search":    ("執行向量檢索測試 [query] [--school]",      None),  # 特殊處理
    "rag":       ("執行完整 RAG 流程 [query] [--school]",    None),  # 特殊處理
    "init-all":  ("一次完成 setup + import",                 lambda: (setup_db() and import_json())),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__.strip())
        print("\n可用指令:")
        for cmd, (desc, _) in COMMANDS.items():
            print(f"  {cmd:<12}  {desc}")
        sys.exit(1)

    cmd = sys.argv[1]
    _, runner = COMMANDS[cmd]

    # search / rag 需要特殊處理（自訂 query 與旗標）
    if cmd in ["search", "rag"]:
        # 解析旗標
        evaluate  = "--eval" in sys.argv
        use_mq    = "--mq" in sys.argv or "--multi-query" in sys.argv
        school_id = None
        if "--school" in sys.argv:
            idx = sys.argv.index("--school")
            if idx + 1 < len(sys.argv):
                school_id = sys.argv[idx + 1]

        # 取出 query（排除旗標）
        skip_keywords = {"--eval", "--mq", "--multi-query", "--school"}
        args_clean = [
            a for i, a in enumerate(sys.argv[2:])
            if a not in skip_keywords and (i == 0 or sys.argv[i + 1] != "--school")
        ]
        query = " ".join(args_clean).strip()

        if not query:
            query = input(f"請輸入查詢問題: ").strip()
            if not query:
                print("未輸入問題，停止執行。")
                sys.exit(0)

        if cmd == "search":
            ok = run_search(query, school_id=school_id)
        else:
            ok = run_rag_pipeline(
                query,
                evaluate=evaluate,
                use_multi_query=use_mq,
                school_id=school_id,
            )
    else:
        ok = runner()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
