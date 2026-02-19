# Study Abroad RAG — North America CS Master’s

RAG-based tool for applying to North America CS master’s programs. Pulls in official requirements (GPA, TOEFL, deadlines) and Reddit-style experience; surfaces both and helps resolve conflicts.

**Stack:** Gemini 2.5 Flash, `BAAI/bge-m3` embeddings, PostgreSQL + pgvector, LangChain, FastAPI. Scraping via Firecrawl / LLM extraction.

**Flow:** Scrape → structure into Postgres (hard facts) + chunk & embed into pgvector (text). Query = SQL filter + vector search; results + user profile go to LLM for advice.

---

## db/

- `init_db.sql` — table definitions (universities, requirements, deadlines)
- `exported_data.sql` — current DB dump for inspection

## scripts/

- **`run.py`** — main entry: DB setup, import, verify, export
- `db/` — modules: connection, setup, import_data, verify, export_data

**Quick start:**

1. Copy `.env.example` → `.env`, set `DATABASE_URL`
2. `pip install -r requirements.txt`
3. From project root:
   - `python scripts/run.py setup` — init DB
   - `python scripts/run.py import` — create tables, import `web_crawler/*.json`
   - `python scripts/run.py verify` — check data
   - `python scripts/run.py export` — write `db/exported_data.sql`
