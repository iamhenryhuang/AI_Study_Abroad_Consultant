#!/usr/bin/env python3
"""
驗證 document_chunks 資料表中的向量與 metadata 是否已正確寫入。
"""
import os
import json
import sys
from pathlib import Path

# 讓 scripts 目錄在 path 中
CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db.connection import get_connection

def verify_embeddings():
    """檢查向量資料庫內容。"""
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cur = conn.cursor()

        # 1. 基本 chunk 清單
        cur.execute("""
            SELECT school_id, chunk_index, source,
                   LEFT(chunk_text, 70)    AS preview,
                   embedding IS NOT NULL   AS has_vector,
                   university_id IS NOT NULL AS has_fk,
                   metadata IS NOT NULL    AS has_meta
            FROM document_chunks
            ORDER BY school_id, source, chunk_index
        """)
        rows = cur.fetchall()

        print(f"Total chunks in DB: {len(rows)}")
        print(f"{'school_id':<15} {'source':<10} {'chunk#':<7} {'vector':<8} {'fk':<5} {'meta':<6} preview")
        print("-" * 110)
        for school_id, idx, source, preview, has_vec, has_fk, has_meta in rows:
            print(f"{school_id:<15} {source:<10} {idx:<7} {str(has_vec):<8} {str(has_fk):<5} {str(has_meta):<6} {preview!r}")

        # 2. 向量維度
        cur.execute("SELECT embedding FROM document_chunks LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            vec = row[0]
            # pgvector 回傳的是 list 或 string
            dims = len(vec) if isinstance(vec, (list, tuple)) else len(vec.strip("[]").split(","))
            print(f"\n向量維度: {dims}")

        return True
    except Exception as e:
        print(f"驗證失敗: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    verify_embeddings()
