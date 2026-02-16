"""檢查資料是否已寫入資料庫。"""
import psycopg2

from .connection import DATABASE_URL, get_connection


def run():
    if not DATABASE_URL:
        print("錯誤: 未設定 DATABASE_URL（.env）。")
        return False
    try:
        conn = get_connection()
        if not conn:
            return False
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM universities")
            count = cur.fetchone()[0]
            print(f"資料庫中的學校數: {count}")
            cur.execute("SELECT school_id, university, program FROM universities")
            for school_id, name, program in cur.fetchall():
                print(f"  - {school_id}: {name} | {program}")
            cur.execute("SELECT COUNT(*) FROM requirements")
            print(f"requirements 筆數: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM deadlines")
            print(f"deadlines 筆數: {cur.fetchone()[0]}")
        conn.close()
        print("\n✓ 驗證通過：資料已存在於資料庫。")
        return True
    except psycopg2.ProgrammingError as e:
        print(f"資料表不存在或結構錯誤: {e}")
        print("請先執行: python scripts/run.py import")
        return False
    except Exception as e:
        print(f"連線或查詢錯誤: {e}")
        return False
