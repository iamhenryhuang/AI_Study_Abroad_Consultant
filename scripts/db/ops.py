"""
ops.py — 資料庫操作集合（v2）

配合新的資料庫 schema：
  - universities  (school_id, name, domain)
  - web_pages     (university_id, url, page_type, raw_text)
  - document_chunks (page_id, school_id, source_url, chunk_text, embedding, metadata)

給 scripts/run.py 呼叫的指令集。
"""

import json
from datetime import datetime

import psycopg2

from .connection import DATABASE_URL, ROOT, get_connection


# ── 工具函式 ──────────────────────────────────────────────────

def _escape_sql(s):
    if s is None:
        return "NULL"
    if isinstance(s, bool):
        return "TRUE" if s else "FALSE"
    if isinstance(s, (int, float)):
        return str(s)
    s = str(s).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


# ── setup_db ─────────────────────────────────────────────────

def setup_db():
    """檢查連線並在需要時建立 study_abroad 資料庫。"""
    url = DATABASE_URL
    if not url or "/study_abroad" not in url:
        print("錯誤: .env 中 DATABASE_URL 需指向 study_abroad（或欲建立的 DB 名稱）。")
        return False
    postgres_url = url.replace("/study_abroad", "/postgres")
    try:
        print(f"連線至: {postgres_url.split('@')[-1]}")
        conn = psycopg2.connect(postgres_url)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'study_abroad'")
            if not cur.fetchone():
                print("建立資料庫 study_abroad ...")
                cur.execute("CREATE DATABASE study_abroad")
                print("已建立 study_abroad。")
            else:
                print("資料庫 study_abroad 已存在。")
        conn.close()
        print("連線測試通過。")
        return True
    except Exception as e:
        print(f"失敗: {e}")
        return False


# ── import_json ──────────────────────────────────────────────

def import_json(data_dirname: str = "data"):
    """
    依 db/init_db.sql 建表，並啟動 embedder/pipeline.py 的 run_pipeline。
    
    新格式的 JSON 匯入邏輯完全由 pipeline.py 處理，
    此函式負責：
      1. 建立/重置資料表（執行 init_db.sql）
      2. 呼叫 pipeline.run_pipeline()
    """
    conn = get_connection()
    if not conn:
        print("請在 .env 設定 DATABASE_URL。")
        return False
    try:
        # 1. 建表
        sql_path = ROOT / "db" / "init_db.sql"
        if not sql_path.is_file():
            print(f"找不到 {sql_path}")
            return False
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text(encoding="utf-8"))
        conn.commit()
        conn.close()
        print("已依 init_db.sql 建立/重置資料表。")
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"建表失敗: {e}")
        return False

    # 2. 執行 pipeline（切片 + 向量化 + 寫入）
    import sys
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))

    from embedder.pipeline import run_pipeline
    return run_pipeline(data_dirname)


# ── verify ───────────────────────────────────────────────────

def verify():
    """檢查資料是否已寫入資料庫（v2 schema）。"""
    if not DATABASE_URL:
        print("錯誤: 未設定 DATABASE_URL（.env）。")
        return False
    try:
        conn = get_connection()
        if not conn:
            return False
        with conn.cursor() as cur:
            # universities
            cur.execute("SELECT COUNT(*) FROM universities")
            print(f"\nuniversities 筆數: {cur.fetchone()[0]}")
            cur.execute("SELECT school_id, name, domain FROM universities ORDER BY id")
            for sid, name, domain in cur.fetchall():
                print(f"   - {sid}: {name} ({domain})")

            # web_pages
            cur.execute("SELECT COUNT(*) FROM web_pages")
            print(f"\nweb_pages 筆數: {cur.fetchone()[0]}")
            cur.execute("""
                SELECT u.school_id, wp.page_type, COUNT(*) 
                FROM web_pages wp
                JOIN universities u ON wp.university_id = u.id
                GROUP BY u.school_id, wp.page_type
                ORDER BY u.school_id, wp.page_type
            """)
            for sid, ptype, cnt in cur.fetchall():
                print(f"   [{sid}][{ptype}] {cnt} 頁")

            # document_chunks
            cur.execute("SELECT COUNT(*) FROM document_chunks")
            print(f"\ndocument_chunks 筆數: {cur.fetchone()[0]}")
            cur.execute("""
                SELECT school_id, page_type, COUNT(*)
                FROM document_chunks
                GROUP BY school_id, page_type
                ORDER BY school_id, page_type
            """)
            for sid, ptype, cnt in cur.fetchall():
                print(f"   [{sid}][{ptype}] {cnt} chunks")

        conn.close()
        print("\n驗證通過：資料已存在於資料庫。")
        return True
    except psycopg2.ProgrammingError as e:
        print(f"資料表不存在或結構錯誤: {e}")
        print("請先執行: python scripts/run.py import")
        return False
    except Exception as e:
        print(f"連線或查詢錯誤: {e}")
        return False


# ── export_sql ───────────────────────────────────────────────

def export_sql():
    """將 universities 與 web_pages 摘要匯出成 db/exported_data.sql。"""
    if not DATABASE_URL:
        print("錯誤: 未設定 DATABASE_URL（.env）。")
        return False
    out_path = ROOT / "db" / "exported_data.sql"
    try:
        conn = get_connection()
        if not conn:
            return False
        cur = conn.cursor()
        lines = [
            "-- 從資料庫匯出的資料（v2 schema）",
            f"-- 匯出時間: {datetime.now().isoformat()}",
            "",
        ]

        # universities
        cur.execute("SELECT id, school_id, name, domain, created_at FROM universities ORDER BY id")
        rows = cur.fetchall()
        if rows:
            lines.append("-- ========== universities ==========")
            for id_, sid, name, domain, created_at in rows:
                ts = f"'{created_at}'" if created_at else "NULL"
                lines.append(
                    f"INSERT INTO universities (id, school_id, name, domain, created_at) VALUES "
                    f"({id_}, {_escape_sql(sid)}, {_escape_sql(name)}, {_escape_sql(domain)}, {ts});"
                )
            lines.append(f"SELECT setval(pg_get_serial_sequence('universities', 'id'), {max(r[0] for r in rows)});")
            lines.append("")

        # web_pages（只匯出 metadata，不含 raw_text 以節省空間）
        cur.execute("""
            SELECT id, university_id, url, page_type, char_count, created_at
            FROM web_pages ORDER BY id
        """)
        rows = cur.fetchall()
        if rows:
            lines.append("-- ========== web_pages (metadata only, raw_text excluded) ==========")
            for id_, uid, url, ptype, char_cnt, created_at in rows:
                ts = f"'{created_at}'" if created_at else "NULL"
                lines.append(
                    f"-- page_id={id_}, university_id={uid}, page_type={_escape_sql(ptype)}, "
                    f"chars={char_cnt}: {_escape_sql(url)}"
                )
            lines.append("")

        # document_chunks 統計
        cur.execute("""
            SELECT school_id, page_type, COUNT(*) as cnt
            FROM document_chunks
            GROUP BY school_id, page_type
            ORDER BY school_id, page_type
        """)
        rows = cur.fetchall()
        lines.append("-- ========== document_chunks 統計 ==========")
        for sid, ptype, cnt in rows:
            lines.append(f"-- [{sid}][{ptype}] {cnt} chunks")

        cur.close()
        conn.close()
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"已匯出至 {out_path}")
        return True
    except Exception as e:
        print(f"匯出失敗: {e}")
        return False
