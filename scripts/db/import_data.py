"""依 db/init_db.sql 建表，並將 web_crawler/*.json 匯入。"""
import json
from datetime import datetime

import psycopg2

from .connection import ROOT, get_connection


def _parse_date(date_str):
    if not date_str or date_str == "Not Available":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def run():
    conn = get_connection()
    if not conn:
        print("請在 .env 設定 DATABASE_URL。")
        return False
    try:
        # 建表
        sql_path = ROOT / "db" / "init_db.sql"
        if not sql_path.is_file():
            print(f"找不到 {sql_path}")
            return False
        with conn.cursor() as cur:
            cur.execute(sql_path.read_text(encoding="utf-8"))
        conn.commit()
        print("已依 init_db.sql 建立/重置資料表。")

        # 匯入 JSON
        web_dir = ROOT / "web_crawler"
        if not web_dir.is_dir():
            print(f"找不到目錄 {web_dir}")
            return False
        json_files = sorted(web_dir.glob("*.json"))
        for path in json_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO universities (school_id, university, program, official_link, description)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (school_id) DO UPDATE SET
                        university = EXCLUDED.university,
                        program = EXCLUDED.program,
                        official_link = EXCLUDED.official_link,
                        description = EXCLUDED.description
                    RETURNING id;
                """, (
                    data["school_id"],
                    data["university"],
                    data["program"],
                    data.get("official_link"),
                    data.get("description_for_vector_db"),
                ))
                university_id = cur.fetchone()[0]

                req = data.get("requirements", {})
                toefl = req.get("toefl", {})
                ielts = req.get("ielts", {})
                gre = req.get("gre", {})
                cur.execute("DELETE FROM requirements WHERE university_id = %s", (university_id,))
                cur.execute("""
                    INSERT INTO requirements (
                        university_id, toefl_min_total, toefl_required, toefl_notes,
                        ielts_min_total, ielts_required, gre_status, gre_notes,
                        minimum_gpa, recommendation_letters, interview_required
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                """, (
                    university_id,
                    toefl.get("min_total"),
                    toefl.get("is_required", False),
                    toefl.get("notes"),
                    ielts.get("min_total"),
                    ielts.get("is_required", False),
                    gre.get("status"),
                    gre.get("notes"),
                    req.get("minimum_gpa"),
                    req.get("recommendation_letters"),
                    str(req.get("interview_required", False)),
                ))

                deadlines = data.get("deadlines", {})
                cur.execute("DELETE FROM deadlines WHERE university_id = %s", (university_id,))
                cur.execute("""
                    INSERT INTO deadlines (university_id, fall_intake, spring_intake)
                    VALUES (%s, %s, %s);
                """, (
                    university_id,
                    _parse_date(deadlines.get("fall_intake")),
                    deadlines.get("spring_intake"),
                ))
            conn.commit()
            print(f"  已匯入 {data['school_id']} ({path.name})")
        conn.close()
        print("匯入完成。")
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"匯入失敗: {e}")
        return False
