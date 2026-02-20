# Study Abroad RAG — North America CS Master’s

RAG-based tool for applying to North America CS master’s programs. Pulls in official requirements (GPA, TOEFL, deadlines) and Reddit-style experience; surfaces both and helps resolve conflicts.

**Stack:** Gemini 2.5 Flash, `BAAI/bge-m3` embeddings, PostgreSQL + **pgvector (HNSW Index)**, LangChain, FastAPI. Scraping via Firecrawl / LLM extraction.

**Flow:** Scrape → structure into Postgres (hard facts) + **chunk & embed** into pgvector (text). Query = SQL filter + **vector search**; results + user profile go to LLM for advice.

---

## db/

- `init_db.sql` — table definitions (universities, requirements, deadlines)
- `exported_data.sql` — current DB dump for inspection

## scripts/

- **`run.py`** — main entry: DB operations, embedding pipeline, and RAG search
- `db/` — modules: connection, setup, data import/export
- `embedder/` — modules: text chunking, BGE-M3 embedding, and vector storage
- `retriever/` — modules: vector similarity search logic

**Quick start:**

1. Copy `.env.example` → `.env`, set `DATABASE_URL` and `GOOGLE_API_KEY`
2. `pip install -r requirements.txt`
3. From project root:
   - `python scripts/run.py init-all` — init DB & import JSON
   - `python scripts/run.py embed` — run chunking & embedding pipeline
   - `python scripts/run.py search "your query"` — test RAG retrieval
   - `python scripts/run.py verify-vdb` — check Vector DB status
   - `python scripts/run.py export` — write `db/exported_data.sql`
