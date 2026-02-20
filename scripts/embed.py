#!/usr/bin/env python3
"""
Chunking + Embedding 主程式。
從 data/*.json 讀取 description_for_vector_db，
切片後用 BAAI/bge-m3 轉成向量，寫入 document_chunks 資料表。

使用方式：
  python scripts/run.py embed
"""
import json
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from db.connection import get_connection
from embedder.chunker import chunk_text
from embedder.store import upsert_chunks
from embedder.vectorize import embed_texts


def run_embed(data_dirname: str = "data") -> bool:
    """讀取所有 JSON，切片 → 向量化 → 寫入 DB。"""
    data_dir = ROOT / data_dirname
    if not data_dir.is_dir():
        print(f"找不到目錄 {data_dir}")
        return False

    json_files = sorted(data_dir.glob("*.json"))
    if not json_files:
        print(f"目錄 {data_dir} 下沒有 .json 檔")
        return False

    conn = get_connection()
    if not conn:
        print("無法連線至資料庫，請確認 .env 中的 DATABASE_URL。")
        return False

    total_chunks = 0
    try:
        for path in json_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            school_id = data.get("school_id", path.stem)
            description = data.get("description_for_vector_db", "")

            if not description.strip():
                print(f"  [{school_id}] 無 description_for_vector_db，跳過。")
                continue

            # 組裝結構化 metadata（數字/日期欄位），供 hybrid RAG query WHERE 過濾
            req = data.get("requirements", {})
            deadlines = data.get("deadlines", {})
            meta = {
                "university":             data.get("university"),
                "school_id":              school_id,
                "toefl_min":              req.get("toefl", {}).get("min_total"),
                "toefl_required":         req.get("toefl", {}).get("is_required"),
                "ielts_min":              req.get("ielts", {}).get("min_total"),
                "ielts_required":         req.get("ielts", {}).get("is_required"),
                "minimum_gpa":            req.get("minimum_gpa"),
                "recommendation_letters": req.get("recommendation_letters"),
                "gre_status":             req.get("gre", {}).get("status"),
                "fall_deadline":          deadlines.get("fall_intake"),
                "spring_deadline":        deadlines.get("spring_intake"),
                "interview_required":     req.get("interview_required"),
            }

            # 1. Chunking
            chunks = chunk_text(description)
            print(f"  [{school_id}] 切成 {len(chunks)} 個 chunk")

            # 2. Embedding
            print(f"  [{school_id}] 向量化中...")
            embeddings = embed_texts(chunks)

            # 3. 寫入 DB（含 metadata）
            n = upsert_chunks(conn, school_id, chunks, embeddings, meta)
            total_chunks += n
            print(f"  [{school_id}] ✓ 已寫入 {n} 筆 chunk（含 metadata）")

        print(f"\n✓ 完成！共寫入 {total_chunks} 筆 chunk 至 document_chunks。")
        return True

    except Exception as e:
        conn.rollback()
        print(f"embed 失敗: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    ok = run_embed()
    sys.exit(0 if ok else 1)
