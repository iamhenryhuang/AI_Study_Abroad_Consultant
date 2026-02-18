"""將 chunk 與向量寫入 document_chunks 資料表。"""

from __future__ import annotations

import psycopg2


def upsert_chunks(
    conn: psycopg2.extensions.connection,
    school_id: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    """
    將 chunks 與對應 embeddings 寫入 document_chunks。
    使用 ON CONFLICT (school_id, chunk_index) DO UPDATE 確保冪等。
    回傳寫入筆數。
    """
    if not chunks:
        return 0

    with conn.cursor() as cur:
        # 先刪除該 school_id 舊有的 chunk（若 chunk 數量改變時保持乾淨）
        cur.execute("DELETE FROM document_chunks WHERE school_id = %s", (school_id,))

        for idx, (text, emb) in enumerate(zip(chunks, embeddings)):
            cur.execute(
                """
                INSERT INTO document_chunks (school_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s::vector)
                ON CONFLICT (school_id, chunk_index) DO UPDATE SET
                    chunk_text = EXCLUDED.chunk_text,
                    embedding  = EXCLUDED.embedding;
                """,
                (school_id, idx, text, str(emb)),
            )
    conn.commit()
    return len(chunks)
