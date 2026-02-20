"""驗證 document_chunks 資料表中的向量與 metadata 是否已正確寫入。"""
import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

# ── 1. 基本 chunk 清單 ─────────────────────────────────────────────────────────
cur.execute("""
    SELECT school_id, chunk_index,
           LEFT(chunk_text, 70)    AS preview,
           embedding IS NOT NULL   AS has_vector,
           university_id IS NOT NULL AS has_fk,
           metadata IS NOT NULL    AS has_meta
    FROM document_chunks
    ORDER BY school_id, chunk_index
""")
rows = cur.fetchall()

print(f"Total chunks: {len(rows)}")
print(f"{'school_id':<25} {'chunk#':<7} {'vector':<8} {'fk':<5} {'meta':<6} preview")
print("-" * 100)
for school_id, idx, preview, has_vec, has_fk, has_meta in rows:
    print(f"{school_id:<25} {idx:<7} {str(has_vec):<8} {str(has_fk):<5} {str(has_meta):<6} {preview!r}")

# ── 2. 向量維度 ────────────────────────────────────────────────────────────────
cur.execute("SELECT embedding FROM document_chunks LIMIT 1")
row = cur.fetchone()
if row and row[0]:
    vec = row[0]
    dims = len(vec.strip("[]").split(",")) if isinstance(vec, str) else len(vec)
    print(f"\n向量維度: {dims}")

# ── 3. metadata 內容抽查（每間學校第一個 chunk）─────────────────────────────────
print("\n── metadata 抽查（每間學校 chunk #0）──")
cur.execute("""
    SELECT school_id, metadata
    FROM document_chunks
    WHERE chunk_index = 0
    ORDER BY school_id
""")
for school_id, meta in cur.fetchall():
    if meta:
        # psycopg2 可能回傳 str 或 dict
        m = meta if isinstance(meta, dict) else json.loads(meta)
        print(f"\n[{school_id}]")
        for key in ["university", "toefl_min", "ielts_min", "minimum_gpa",
                    "gre_status", "fall_deadline", "recommendation_letters"]:
            print(f"  {key:<25}: {m.get(key)}")
    else:
        print(f"\n[{school_id}] ⚠ metadata 為 NULL")

# ── 4. university_id FK 對照 ──────────────────────────────────────────────────
print("\n── university_id FK 對照 ──")
cur.execute("""
    SELECT dc.school_id, dc.university_id, u.university
    FROM document_chunks dc
    LEFT JOIN universities u ON dc.university_id = u.id
    WHERE dc.chunk_index = 0
    ORDER BY dc.school_id
""")
for school_id, uid, uname in cur.fetchall():
    status = "✓" if uid else "⚠ NULL"
    print(f"  {school_id:<30} university_id={uid} {status}  {uname or ''}")

conn.close()
