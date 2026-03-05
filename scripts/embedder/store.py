"""
store.py — 向量存入 DB 的輕量包裝（v2）

注意：v2 主要邏輯已移入 pipeline.py 的 upsert_chunks()。
此模組保留供其他腳本（如 reddit_pipeline.py）呼叫使用。
"""

from __future__ import annotations

import json as _json

import psycopg2


def upsert_chunks_by_page(
    conn: psycopg2.extensions.connection,
    university_id: int,
    page_id: int,
    school_id: str,
    source_url: str,
    page_type: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    """
    以 (page_id, chunk_index) 為 key，刪舊插新。
    回傳寫入筆數。

    Args:
        conn:          psycopg2 連線
        university_id: 對應的 universities.id
        page_id:       對應的 web_pages.id
        school_id:     學校識別碼（e.g. 'cmu'）
        source_url:    原始 URL（存入 metadata 供回答時引用）
        page_type:     頁面類型（'admissions'/'faq' 等）
        chunks:        切片後的文字列表
        embeddings:    對應的向量列表
    """
    if not chunks:
        return 0

    meta_base = {
        "school_id":  school_id,
        "page_type":  page_type,
        "source_url": source_url,
    }
    meta_json = _json.dumps(meta_base, ensure_ascii=False)

    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_chunks WHERE page_id = %s", (page_id,))

        for idx, (text, emb) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                """
                INSERT INTO document_chunks
                    (university_id, page_id, school_id, source_url, page_type,
                     chunk_index, chunk_text, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                ON CONFLICT (page_id, chunk_index) DO UPDATE SET
                    chunk_text    = EXCLUDED.chunk_text,
                    embedding     = EXCLUDED.embedding,
                    metadata      = EXCLUDED.metadata;
                """,
                (
                    university_id, page_id, school_id, source_url, page_type,
                    idx, text, str(emb), meta_json,
                ),
            )
    conn.commit()
    return len(chunks)
