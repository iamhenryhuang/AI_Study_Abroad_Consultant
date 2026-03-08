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
├── professor_fetcher/
│   ├── fetcher.py          ← SerpAPI tool to search & fetch Scholar data
│   ├── formatter.py        ← convert API data to project-standard JSON
│   └── run_fetch.py        ← CLI: fetch single/batch professors + optional --embed
├── retriever/
│   ├── search.py           ← vector search (HNSW), optional school_id/page_type filter
│   ├── reranker.py         ← Cross-Encoder reranking (BAAI/bge-reranker-v2-m3)
│   ├── multi_query.py      ← Multi-Query expansion via Gemini
│   ├── agent.py            ← Agentic RAG: Gemini Function Calling ReAct loop
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
| `python -m scripts.professor_fetcher.run_fetch --name "Name" --school "School"` | Fetch professor data |
| `python -m scripts.professor_fetcher.run_fetch --config config.json --embed` | Batch fetch + embed |

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
```

**Flags:**

| `--school cmu` | Filter retrieval to a single school (`cmu`, `caltech`, …) |
| `--mq` | Enable Multi-Query expansion (Gemini generates 3 related queries) |
| `--max-steps N` | Max ReAct iterations for `agent` command (default: 5) |

---

## Professor Data Fetching (SerpAPI)

Fetches a professor's research areas and recent papers from Google Scholar. Results are stored in `data/{school_id}_professors.json` and automatically integrated during `import` or `init-all`.

### Setup
1. Get a **SerpAPI Key** at [serpapi.com](https://serpapi.com).
2. Add to `.env`: `SERPAPI_KEY=your_key`.

### Usage
Run from project root:

```bash
# Single professor (searches for author_id automatically)
python -m scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school "Stanford"

# Single professor + immediate embedding
python -m scripts.professor_fetcher.run_fetch --name "Fei-Fei Li" --school "Stanford" --embed

# Batch mode from config
python -m scripts.professor_fetcher.run_fetch --config professors.json --embed

# Format of professors.json:
# [
#   {"name": "Andrew Ng", "school": "Stanford", "school_id": "stanford"},
#   {"name": "Yann LeCun", "school": "NYU", "school_id": "nyu"}
# ]
```

**Common Flags:**
- `--author-id "ID"`: Skip search if ID is known (e.g., `47730H0AAAAJ`).
- `--cutoff-year 2024`: Only fetch papers from this year onwards.
- `--max-papers 20`: Limit recent paper count.
- `--embed`: Automatically run the embedding pipeline after fetching.

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
| `professor_profile` | professor_profile | 1800 | 200 | Large profile context |
| `professor_paper` | professor_paper | 1000 | 150 | Precise paper details |
| *(anything else)* | general | 1400 | 200 | |

### Database schema (v2)

```
universities  →  web_pages  →  document_chunks
                 (one per URL)  (one per chunk, with source_url + HNSW vector)
```

---

---

## Requirements

- PostgreSQL with `pgvector` extension enabled
- Local model files (paths set in `.env`):
  - `BGE_EMBED_MODEL_PATH` — path to `BAAI/bge-m3`
  - `BGE_RERANKER_MODEL_PATH` — path to `BAAI/bge-reranker-v2-m3`
- API Keys:
  - `GOOGLE_API_KEY` (Gemini)
  - `SERPAPI_KEY` (Professor Fetcher)
- Python dependencies: `pip install -r requirements.txt`
