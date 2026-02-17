"""將資料庫內容匯出成 db/exported_data.sql。"""
from datetime import datetime

import psycopg2

from .connection import DATABASE_URL, ROOT, get_connection


def _escape_sql(s):
    if s is None:
        return "NULL"
    if isinstance(s, bool):
        return "TRUE" if s else "FALSE"
    if isinstance(s, (int, float)):
        return str(s) if s is not None else "NULL"
    s = str(s).replace("\\", "\\\\").replace("'", "''")
    return f"'{s}'"


def run():
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
                (id_, university_id, toefl_min, toefl_req, toefl_notes, ielts_min, ielts_req,
                 ielts_notes, gre_status, gre_notes, gpa, rec_letters, interview) = r
                vals = [
                    str(id_), str(university_id),
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
