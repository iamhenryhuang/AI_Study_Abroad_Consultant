"""將 chunk 與向量寫入 document_chunks 資料表。"""

from __future__ import annotations

import json as _json

import psycopg2


def upsert_chunks(
    conn: psycopg2.extensions.connection,
    school_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
    meta: dict | None = None,
    source: str = "official",
) -> int:
    """
    將 chunks 與對應 embeddings 寫入 document_chunks。
    - meta: 一個 dict，包含該學校的結構化數字/日期欄位 (toefl_min、fall_deadline 等)，
            會以 JSONB 形式存入 metadata 欄位，供 hybrid RAG query 做 WHERE 過濾。
    - source: 來源，例如 'official' 或 'reddit'。
    使用 DELETE + INSERT 確保 chunk 數量改變時資料乾淨。
    回傳寫入筆數。
    """
    if not chunks:
        return 0

    meta_json = _json.dumps(meta, ensure_ascii=False) if meta else None

    with conn.cursor() as cur:
        # 查出 university_id（供 FK 欄位使用）
        cur.execute("SELECT id FROM universities WHERE school_id = %s", (school_id,))
        row = cur.fetchone()
        university_id = row[0] if row else None

        # 先刪除該 school_id 且來源相同的舊有 chunk（確保 chunk 數量改變時資料乾淨）
        cur.execute(
            "DELETE FROM document_chunks WHERE school_id = %s AND source = %s",
            (school_id, source)
        )

        for idx, (text, emb) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                """
                INSERT INTO document_chunks
                    (school_id, university_id, source, chunk_index, chunk_text, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s::jsonb)
                ON CONFLICT (school_id, source, chunk_index) DO UPDATE SET
                    chunk_text    = EXCLUDED.chunk_text,
                    embedding     = EXCLUDED.embedding,
                    university_id = EXCLUDED.university_id,
                    metadata      = EXCLUDED.metadata;
                """,
                (school_id, university_id, source, idx, text, str(emb), meta_json),
            )
    conn.commit()
    return len(chunks)
