# Study Abroad RAG — North America CS Master's

RAG-based consultant for applying to North American CS master's programs. Crawls official university pages and processes the raw text into a vector database for semantic retrieval and LLM-powered advice.

**Stack:** Gemini 2.5 Flash · `BAAI/bge-m3` embeddings · PostgreSQL + **pgvector (HNSW)** · LangChain · Cross-Encoder reranking

**Flow:** Crawl URLs → store raw text → chunk by page type → embed → pgvector. Query → vector search (+ optional school filter) → rerank → Gemini answer.

---

## Data Format

`data/*.json` (e.g., `caltech.json`, `cmu.json`) uses a flat `{ url: raw_text }` structure:

```json
{
  "https://www.cs.cmu.edu/academics/graduate-admissions": "Carnegie Mellon University...",
  "https://www.gradoffice.caltech.edu/admissions/faq-applicants": "Frequently Asked Questions..."
}
```

The pipeline processes every JSON in the `data/` folder. The school (`cmu`, `caltech`, …) is inferred automatically from the URL domain or the filename. To add a new school, update `SCHOOL_MAP` in `scripts/embedder/pipeline.py`.

---

## Project Structure

```
data/
  *.json                ← { url: raw_text } — school-specific JSON files
db/
  init_db.sql           ← schema: universities + web_pages + document_chunks
scripts/
  run.py                ← unified entry point
  db/                   ← connection, setup, import/export
  embedder/             ← chunker, pipeline, vectorize, store, verifier
  retriever/            ← search, reranker, multi_query, rag_pipeline, agent
  generator/            ← Gemini answer generation
```

---

## Quick Start

1. Copy `.env.example` → `.env`, fill in `DATABASE_URL` and `GOOGLE_API_KEY`
2. `pip install -r requirements.txt`
3. From the project root:

```bash
# First-time setup: create DB + build tables + chunk + embed (all-in-one)
python scripts/run.py init-all

# Or step by step:
python scripts/run.py setup       # create study_abroad database
python scripts/run.py import      # build schema, chunk, embed & store

# Verify
python scripts/run.py verify-db   # check SQL tables
python scripts/run.py verify-vdb  # check chunk counts & vector dims

# Search & RAG
python scripts/run.py search "CMU SCS admission requirements"
python scripts/run.py search "Caltech PhD funding" --school caltech

python scripts/run.py rag "What are CMU MSCS requirements?"
python scripts/run.py rag "Compare CMU and Caltech deadlines" --school cmu --mq

# Agentic RAG (ReAct Loop — 自動决定搜尋次數與策略)
python scripts/run.py agent "Compare GPA requirements and deadlines for Stanford, CMU and MIT"
python scripts/run.py agent "What do admitted students say about the CMU MSCS interview?" --max-steps 6

# Export SQL summary
python scripts/run.py export
```

---

## Chunk Strategy by Page Type

Chunks are sized for **English text** (~5–6 chars/word). FAQ pages use a regex pre-pass to extract whole Q&A pairs before splitting.

| URL contains | page_type | chunk_size | overlap |
|---|---|---|---|
| `faq` | faq | 2000 chars (Q&A pre-split) | 200 |
| `checklist` / `requirements` | checklist | 1200 chars | 150 |
| `admissions` / `apply` | admissions | 1600 chars | 200 |
| `reddit.com` | reddit | 900 chars | 150 |
| anything else | general | 1400 chars | 200 |
