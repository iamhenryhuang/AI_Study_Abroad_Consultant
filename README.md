# Study Abroad RAG — North America CS Master’s

RAG-based tool for applying to North America CS master’s programs. Pulls in official requirements (GPA, TOEFL, deadlines) and Reddit-style experience; surfaces both and helps resolve conflicts.

**Stack:** Gemini 2.5 Flash, `BAAI/bge-m3` embeddings, PostgreSQL + **pgvector (HNSW Index)**, LangChain, FastAPI. Scraping via Firecrawl / LLM extraction.

**Flow:** Scrape → structure into Postgres (hard facts) + **chunk & embed** into pgvector (text). Query = SQL filter + **vector search**; results + user profile go to LLM for advice.

---

## data/ & reddit_data/

- `data/` — official university requirements (GPA, TOEFL, GRE, deadlines)
- `reddit_data/` — community posts and application experiences from Reddit

## scripts/

- **`run.py`** — main entry: DB operations, embedding pipeline, and RAG search
- `db/` — modules: connection, setup, data import/export
- `embedder/` — modules: official and reddit specific embedding pipelines
- `retriever/` — modules: vector similarity search and RAG orchestration
- `evaluator/` — modules: RAG Triad evaluation using Gemini as a judge

**Quick start:**

1. Copy `.env.example` → `.env`, set `DATABASE_URL` and `GOOGLE_API_KEY`
2. `pip install -r requirements.txt`
3. From project root:
   - `python scripts/run.py init-all` — init DB & import official JSON
   - `python scripts/run.py embed` — run official embedding pipeline
   - `python scripts/run.py embed-reddit` — run reddit-specific embedding pipeline
   - `python scripts/run.py rag "your query" --eval` — execute RAG answer with adaptive prompts
   - `python scripts/run.py rag "your query" --mq` — execute RAG with Multi-Query expansion
   - `python scripts/run.py search "your query"` — test RAG retrieval (shows official vs reddit source)
   - `python scripts/run.py verify-vdb` — check Vector DB status (official/reddit breakdown)
   - `python scripts/run.py export` — write `db/exported_data.sql`
