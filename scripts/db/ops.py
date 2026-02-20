"""資料庫操作集合（給 scripts/run.py 呼叫）。"""

import json
from datetime import datetime

import psycopg2

from .connection import DATABASE_URL, ROOT, get_connection


def _parse_date(date_str):
    if not date_str or date_str == "Not Available":
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None


def _escape_sql(s):
    if s is None:
        return "NULL"
    if isinstance(s, bool):
        return "TRUE" if s else "FALSE"
    if isinstance(s, (int, float)):
        return str(s) if s is not None else "NULL"
    s = str(s).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


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


def import_json(data_dirname: str = "data"):
    """依 db/init_db.sql 建表，並將 data_dirname/*.json 匯入。"""
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
        data_dir = ROOT / data_dirname
        if not data_dir.is_dir():
            print(f"找不到目錄 {data_dir}")
            return False
        json_files = sorted(data_dir.glob("*.json"))
        if not json_files:
            print(f"目錄 {data_dir} 下沒有 .json 檔")
            return False

        for path in json_files:
            data = json.loads(path.read_text(encoding="utf-8"))
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO universities (school_id, university, program, official_link, description)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (school_id) DO UPDATE SET
                        university = EXCLUDED.university,
                        program = EXCLUDED.program,
                        official_link = EXCLUDED.official_link,
                        description = EXCLUDED.description
                    RETURNING id;
                    """,
                    (
                        data["school_id"],
                        data["university"],
                        data["program"],
                        data.get("official_link"),
                        data.get("description_for_vector_db"),
                    ),
                )
                university_id = cur.fetchone()[0]

                req = data.get("requirements", {})
                toefl = req.get("toefl", {})
                ielts = req.get("ielts", {})
                gre = req.get("gre", {})
                cur.execute("DELETE FROM requirements WHERE university_id = %s", (university_id,))
                cur.execute(
                    """
                    INSERT INTO requirements (
                        university_id, toefl_min_total, toefl_required, toefl_notes,
                        ielts_min_total, ielts_required, gre_status, gre_notes,
                        minimum_gpa, recommendation_letters, interview_required
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
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
                    ),
                )

                deadlines = data.get("deadlines", {})
                cur.execute("DELETE FROM deadlines WHERE university_id = %s", (university_id,))
                cur.execute(
                    """
                    INSERT INTO deadlines (university_id, fall_intake, spring_intake)
                    VALUES (%s, %s, %s);
                    """,
                    (
                        university_id,
                        _parse_date(deadlines.get("fall_intake")),
                        deadlines.get("spring_intake"),
                    ),
                )
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


def verify():
    """檢查資料是否已寫入資料庫。"""
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
            cur.execute("SELECT school_id, university, program FROM universities ORDER BY id")
            for school_id, name, program in cur.fetchall():
                print(f"  - {school_id}: {name} | {program}")
            cur.execute("SELECT COUNT(*) FROM requirements")
            print(f"requirements 筆數: {cur.fetchone()[0]}")
            cur.execute("SELECT COUNT(*) FROM deadlines")
            print(f"deadlines 筆數: {cur.fetchone()[0]}")
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


def export_sql():
    """將資料庫內容匯出成 db/exported_data.sql。"""
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
            "-- 從資料庫匯出的資料（寫入 SQL 的內容）",
            f"-- 匯出時間: {datetime.now().isoformat()}",
            "-- 僅供檢視；若要還原請先執行 db/init_db.sql 再依序執行下列 INSERT。",
            "",
        ]

        cur.execute(
            "SELECT id, school_id, university, program, official_link, description, created_at FROM universities ORDER BY id"
        )
        rows = cur.fetchall()
        if rows:
            lines.append("-- ========== universities ==========")
            for r in rows:
                id_, school_id, university, program, official_link, description, created_at = r
                ts = f"'{created_at}'" if created_at else "NULL"
                lines.append(
                    f"INSERT INTO universities (id, school_id, university, program, official_link, description, created_at) VALUES "
                    f"({id_}, {_escape_sql(school_id)}, {_escape_sql(university)}, {_escape_sql(program)}, {_escape_sql(official_link)}, {_escape_sql(description)}, {ts});"
                )
            lines.append("")
            max_id = max(r[0] for r in rows)
            lines.append(f"SELECT setval(pg_get_serial_sequence('universities', 'id'), {max_id});")
            lines.append("")
        else:
            lines.append("-- (無 universities 資料)")
            lines.append("")

        cur.execute(
            """SELECT id, university_id, toefl_min_total, toefl_required, toefl_notes,
            ielts_min_total, ielts_required, ielts_notes, gre_status, gre_notes,
            minimum_gpa, recommendation_letters, interview_required FROM requirements ORDER BY id"""
        )
        rows = cur.fetchall()
        if rows:
            lines.append("-- ========== requirements ==========")
            for r in rows:
                (
                    id_,
                    university_id,
                    toefl_min,
                    toefl_req,
                    toefl_notes,
                    ielts_min,
                    ielts_req,
                    ielts_notes,
                    gre_status,
                    gre_notes,
                    gpa,
                    rec_letters,
                    interview,
                ) = r
                vals = [
                    str(id_),
                    str(university_id),
                    str(toefl_min) if toefl_min is not None else "NULL",
                    "TRUE" if toefl_req else "FALSE",
                    _escape_sql(toefl_notes),
                    str(ielts_min) if ielts_min is not None else "NULL",
                    "TRUE" if ielts_req else "FALSE",
                    _escape_sql(ielts_notes),
                    _escape_sql(gre_status),
                    _escape_sql(gre_notes),
                    str(gpa) if gpa is not None else "NULL",
                    str(rec_letters) if rec_letters is not None else "NULL",
                    _escape_sql(interview),
                ]
                lines.append(
                    "INSERT INTO requirements (id, university_id, toefl_min_total, toefl_required, toefl_notes, "
                    "ielts_min_total, ielts_required, ielts_notes, gre_status, gre_notes, "
                    "minimum_gpa, recommendation_letters, interview_required) VALUES (" + ", ".join(vals) + ");"
                )
            lines.append("")
            max_id = max(r[0] for r in rows)
            lines.append(f"SELECT setval(pg_get_serial_sequence('requirements', 'id'), {max_id});")
            lines.append("")
        else:
            lines.append("-- (無 requirements 資料)")
            lines.append("")

        cur.execute("SELECT id, university_id, fall_intake, spring_intake FROM deadlines ORDER BY id")
        rows = cur.fetchall()
        if rows:
            lines.append("-- ========== deadlines ==========")
            for r in rows:
                id_, university_id, fall_intake, spring_intake = r
                fall = f"'{fall_intake}'" if fall_intake else "NULL"
                lines.append(
                    f"INSERT INTO deadlines (id, university_id, fall_intake, spring_intake) VALUES "
                    f"({id_}, {university_id}, {fall}, {_escape_sql(spring_intake)});"
                )
            lines.append("")
            max_id = max(r[0] for r in rows)
            lines.append(f"SELECT setval(pg_get_serial_sequence('deadlines', 'id'), {max_id});")
        else:
            lines.append("-- (無 deadlines 資料)")

        cur.close()
        conn.close()
        out_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"已匯出至 {out_path}")
        return True
    except Exception as e:
        print(f"匯出失敗: {e}")
        return False

