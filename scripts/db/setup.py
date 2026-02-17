"""檢查連線並在需要時建立 study_abroad 資料庫。"""
import psycopg2

from .connection import DATABASE_URL


def run():
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
