"""驗證 document_chunks 資料表中的向量是否已正確寫入。"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

cur.execute("""
    SELECT school_id, chunk_index,
           LEFT(chunk_text, 70) AS preview,
           embedding IS NOT NULL AS has_vector
    FROM document_chunks
    ORDER BY school_id, chunk_index
""")
rows = cur.fetchall()

print(f"Total chunks: {len(rows)}")
print(f"{'school_id':<25} {'chunk#':<7} {'has_vector':<12} preview")
print("-" * 90)
for school_id, idx, preview, has_vec in rows:
    print(f"{school_id:<25} {idx:<7} {str(has_vec):<12} {preview!r}")

# 確認向量維度（取第一筆）
cur.execute("SELECT embedding FROM document_chunks LIMIT 1")
row = cur.fetchone()
if row and row[0]:
    # pgvector 回傳的是字串 '[0.1, 0.2, ...]'
    vec = row[0]
    if isinstance(vec, str):
        dims = len(vec.strip("[]").split(","))
    else:
        dims = len(vec)
    print(f"\n向量維度: {dims}")

conn.close()
