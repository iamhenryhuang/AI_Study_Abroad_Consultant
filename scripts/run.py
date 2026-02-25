#!/usr/bin/env python3
"""
資料庫腳本統一入口。請在專案根目錄執行：

  python scripts/run.py setup    # 檢查連線，必要時建立 study_abroad 資料庫
  python scripts/run.py import   # 建表並匯入 data/*.json
  python scripts/run.py verify   # 檢查資料是否已寫入
  python scripts/run.py export   # 匯出至 db/exported_data.sql
  python scripts/run.py init-all # 一次完成 setup + import
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
from embedder.reddit_pipeline import run_reddit_pipeline
from embedder.verifier import verify_embeddings
from retriever.search import run_search
from retriever.rag_pipeline import run_rag_pipeline

COMMANDS = {
    "setup": ("檢查連線並建立資料庫", setup_db),
    "import": ("建表並匯入 data/*.json", import_json),
    "verify-db": ("檢查 SQL 資料是否已寫入", verify),
    "export": ("匯出至 db/exported_data.sql", export_sql),
    "embed": ("切片 + 向量化並寫入 document_chunks", run_pipeline),
    "embed-reddit": ("處理 reddit_data 下的 JSON 並寫入向量庫", run_reddit_pipeline),
    "verify-vdb": ("檢查向量資料庫 (Vector DB) 狀態", verify_embeddings),
    "search": ("執行 RAG 檢索測試", lambda: run_search("UIUC MSCS requirements")),
    "rag": ("執行完整 RAG 回答 (檢索+重排+LLM)", lambda: run_rag_pipeline("CMU MSCS requirement")),
    "init-all": ("建立資料庫並匯入 JSON（setup + import）", lambda: (setup_db() and import_json())),
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
    
    # 對於 search 與 rag 指令，支援自定義 query
    if cmd in ["search", "rag"]:
        if len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])
        else:
            # 如果沒帶參數，則進入互動模式
            query = input(f"請輸入要{cmd}的問題: ").strip()
            if not query:
                print("未輸入問題，停止執行。")
                sys.exit(0)
        
        if cmd == "search":
            ok = run_search(query)
        else:
            # 檢查是否有 --eval 或 --mq 參數
            evaluate = "--eval" in sys.argv
            use_mq = "--mq" in sys.argv or "--multi-query" in sys.argv
            
            # 清理 query 內容
            query = query.replace("--eval", "").replace("--mq", "").replace("--multi-query", "").strip()
            
            ok = run_rag_pipeline(query, evaluate=evaluate, use_multi_query=use_mq)
    else:
        ok = runner()
    
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
