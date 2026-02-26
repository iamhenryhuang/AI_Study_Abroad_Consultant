#!/usr/bin/env python3
"""
verifier.py — 驗證向量資料庫內容（v2）

配合新 schema（web_pages + document_chunks）驗證資料是否正確寫入。
"""
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = CURRENT_DIR.parent
ROOT_DIR = SCRIPTS_DIR.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db.connection import get_connection


def verify_embeddings() -> bool:
    """檢查向量資料庫（v2 schema）內容。"""
    conn = get_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()

        # 1. 學校 + 頁面統計
        cur.execute("""
            SELECT
                u.school_id,
                u.name,
                COUNT(DISTINCT wp.id)  AS page_count,
                COUNT(dc.id)           AS chunk_count,
                SUM(dc.embedding IS NOT NULL::int) AS has_vector
            FROM universities u
            LEFT JOIN web_pages wp ON wp.university_id = u.id
            LEFT JOIN document_chunks dc ON dc.university_id = u.id
            GROUP BY u.id, u.school_id, u.name
            ORDER BY u.school_id
        """)
        rows = cur.fetchall()
        print(f"\n{'學校 ID':<12} {'學校名稱':<40} {'頁面數':<8} {'chunk數':<10} {'向量數'}")
        print("-" * 90)
        for sid, name, pages, chunks, vecs in rows:
            print(f"{sid:<12} {name:<40} {pages:<8} {chunks:<10} {vecs}")

        # 2. 每頁面類型的 chunk 數
        cur.execute("""
            SELECT school_id, page_type, COUNT(*) AS cnt
            FROM document_chunks
            GROUP BY school_id, page_type
            ORDER BY school_id, page_type
        """)
        rows = cur.fetchall()
        print(f"\n{'學校':<12} {'頁面類型':<20} {'chunk數'}")
        print("-" * 45)
        for sid, ptype, cnt in rows:
            print(f"{sid:<12} {ptype:<20} {cnt}")

        # 3. 抽查幾筆 chunk 預覽
        cur.execute("""
            SELECT
                dc.school_id,
                dc.page_type,
                dc.chunk_index,
                dc.source_url,
                LEFT(dc.chunk_text, 80) AS preview,
                dc.embedding IS NOT NULL AS has_vector
            FROM document_chunks dc
            ORDER BY dc.school_id, dc.page_type, dc.chunk_index
            LIMIT 10
        """)
        rows = cur.fetchall()
        print(f"\n--- 抽查前 10 筆 chunk ---")
        for sid, ptype, idx, url, preview, has_vec in rows:
            print(f"  [{sid}][{ptype}] chunk#{idx} vec={has_vec}")
            print(f"    URL: {url[-60:]}")
            print(f"    預覽: {preview!r}")

        # 4. 向量維度確認
        cur.execute("SELECT embedding FROM document_chunks WHERE embedding IS NOT NULL LIMIT 1")
        row = cur.fetchone()
        if row and row[0]:
            vec = row[0]
            dims = len(vec) if isinstance(vec, (list, tuple)) else len(str(vec).strip("[]").split(","))
            print(f"\n向量維度: {dims}")

        print("\n向量資料庫驗證通過。")
        return True

    except Exception as e:
        print(f"驗證失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    verify_embeddings()
