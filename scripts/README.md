# AI Study Abroad Consultant — Scripts

All database, embedding, and retrieval logic lives here. Run everything from the **project root** via `run.py`.

---

## Directory Structure

```
scripts/
├── run.py                  ← unified entry point for all commands
├── db/
│   ├── connection.py       ← PostgreSQL connection (reads DATABASE_URL from .env)
│   └── ops.py              ← setup_db, import_json, verify, export_sql
├── embedder/
│   ├── pipeline.py         ← main pipeline: reads {url:text} JSON → chunks → embeds → stores
│   ├── chunker.py          ← smart chunking: chunk size + strategy adapts to page_type
│   ├── vectorize.py        ← BAAI/bge-m3 embeddings (1024-dim)
│   ├── store.py            ← upsert helper for document_chunks
│   └── verifier.py         ← verify chunk counts, vector dims, source URLs
├── retriever/
│   ├── search.py           ← vector search (HNSW), optional school_id/page_type filter
│   ├── reranker.py         ← Cross-Encoder reranking (BAAI/bge-reranker-v2-m3)
│   ├── multi_query.py      ← Multi-Query expansion via Gemini
│   ├── agent.py            ← Agentic RAG: Gemini Function Calling ReAct loop
│   ├── sanity_check.py     ← pre-LLM validator: flags implausible values (GPA, TOEFL, GRE…)
│   └── rag_pipeline.py     ← full RAG orchestration: search → rerank → generate
└── generator/
    └── gemini.py           ← Gemini 2.5 Flash answer generation
```

---

## Commands

### Database & Import

| Command | What it does |
|---------|-------------|
| `python scripts/run.py setup` | Create the `study_abroad` database |
| `python scripts/run.py import` | Run `init_db.sql` + chunk + embed + store all URLs |
| `python scripts/run.py init-all` | `setup` + `import` in one shot |
| `python scripts/run.py verify-db` | Print table row counts (universities, web_pages, chunks) |
| `python scripts/run.py verify-vdb` | Print chunk/vector breakdown per school & page type |
| `python scripts/run.py export` | Write `db/exported_data.sql` summary |

### Embedding Only

```bash
# Re-run chunking + embedding without resetting tables
python scripts/run.py embed
```

### Search & RAG

```bash
# Vector search only (no LLM generation)
python scripts/run.py search "CMU MSCS application requirements"
python scripts/run.py search "Caltech PhD funding" --school caltech

# Full RAG: search → rerank → Gemini answer
python scripts/run.py rag "What documents does CMU SCS require?"
python scripts/run.py rag "Compare CMU and Caltech funding packages" --mq
python scripts/run.py rag "Stanford MS admission GPA" --school stanford

# Agentic RAG: Gemini 自動决定搜尋次數與策略（ReAct Loop）
python scripts/run.py agent "Compare GPA and deadline for Stanford, CMU, and MIT"
python scripts/run.py agent "What do Reddit users say about CMU MSCS?" --max-steps 6
```

**Flags:**

| Flag | Effect |
|------|--------|
| `--school cmu` | Filter retrieval to a single school (`cmu`, `caltech`, …) |
| `--mq` | Enable Multi-Query expansion (Gemini generates 3 related queries) |
| `--max-steps N` | Max ReAct iterations for `agent` command (default: 5) |

---

## How the Pipeline Works

### Data format

`data/*.json` (e.g., `caltech.json`, `cmu.json`):
```json
{ "https://url1": "raw crawled text...", "https://url2": "raw text..." }
```
The pipeline automatically processes every `.json` file in the `data/` directory.
It uses the URL domain or the file name to identify the school.

The school is inferred from the URL domain (primary) or filename (fallback) via `SCHOOL_MAP` in `pipeline.py`. Currently supported schools:

| school_id | University Name |
|-----------|-----------------|
| `cmu` | Carnegie Mellon University |
| `caltech` | California Institute of Technology |
| `stanford` | Stanford University |
| `berkeley` | UC Berkeley |
| `mit` | MIT |
| `uiuc` | UIUC |
| `gatech` | Georgia Tech |
| `cornell` | Cornell University |
| `ucla` | UCLA |
| `ucsd` | UC San Diego |
| `uw` | University of Washington |

### Chunk strategy by page type

`chunker.py` detects the page type from the URL path and applies an appropriate chunking strategy. All sizes are calibrated for **English text** (~5–6 chars/word, so 1400 chars ≈ 200–250 words).

**FAQ pages** receive special treatment: a regex pre-pass splits the text at question-sentence boundaries (e.g. "Do...", "What...", "How...", "Can...") so that each Q&A pair is kept intact as a single chunk before any character-limit splitting.

| URL path contains | page_type | chunk_size | overlap | Notes |
|-------------------|-----------|-----------|---------|-|
| `faq` | faq | 2000 | 200 | Q&A regex pre-split |
| `checklist` / `requirements` | checklist | 1200 | 150 | |
| `admissions` / `apply` | admissions | 1600 | 200 | |
| `reddit.com` | reddit | 900 | 150 | Short conversational posts |
| *(anything else)* | general | 1400 | 200 | |

### Database schema (v2)

```
universities  →  web_pages  →  document_chunks
                 (one per URL)  (one per chunk, with source_url + HNSW vector)
```

---

## Sanity Check (Agentic RAG only)

`sanity_check.py` runs automatically inside the Agent's tool executor. Before each search result is shown to the LLM, every chunk is scanned for numerically implausible values. Suspicious chunks are annotated with a ⚠️ header so the Agent knows to re-search or warn the user.

| Rule | Trigger |
|---|---|
| `gpa_out_of_range` | GPA > 4.5 or == 0.0 (US 4.0/4.3 scale) |
| `toefl_out_of_range` | TOEFL iBT > 120 |
| `ielts_out_of_range` | IELTS > 9.0 |
| `gre_out_of_range` | GRE value outside 130–340 range |
| `tuition_suspiciously_high` | Dollar amount > $100,000 per entry |

Agent response logic when a ⚠️ flag is detected:
- **Strategy A** — Re-search with different query or `page_type='faq'` to cross-verify
- **Strategy B** — Flag the value in the final answer: *「this figure appears implausible; please verify at [URL]」*
- **Strategy C** — If all results are flagged, tell the user the database data may be unreliable

---

## Requirements

- PostgreSQL with `pgvector` extension enabled
- Local model files (paths set in `.env`):
  - `BGE_EMBED_MODEL_PATH` — path to `BAAI/bge-m3` (default: `D:\DforDownload\BAAI\bge-m3`)
  - `BGE_RERANKER_MODEL_PATH` — path to `BAAI/bge-reranker-v2-m3`
  - Both will auto-download from HuggingFace if the local path does not exist
- Python dependencies: `pip install -r requirements.txt`
- `.env` with `DATABASE_URL`, `GOOGLE_API_KEY`, `BGE_EMBED_MODEL_PATH`, `BGE_RERANKER_MODEL_PATH`
