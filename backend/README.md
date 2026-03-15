# Study Abroad Consultant — Backend

This is the Python-based backend for the Study Abroad RAG Consultant project. It leverages **FastAPI**, **PostgreSQL (pgvector)**, and **Google Gemini** to provide a highly capable, student-centric advisory system.

## Key Features

- **Agentic RAG (ReAct Loop)**: Uses Gemini Function Calling to perform multi-step reasoning, allowing it to search for, compare, and synthesize information across multiple university sources.
- **Dynamic Chunking (v4)**: Context-aware text splitting that injects school and page metadata into every chunk, significantly improving retrieval accuracy.
- **High-Performance Retrieval**: Implements **BGE-M3** embeddings and **HNSW** indexing via `pgvector` for fast and semantic document search.
- **Cross-Encoder Reranking**: Utilizes `bge-reranker-v2-m3` to refine search results, ensuring the most relevant content is prioritized for the LLM.
- **Real-Time SSE**: Streams the agent's thought process and step-by-step tool executions to the frontend via Server-Sent Events.

## Tech Stack

- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **LLM**: [Google Gemini 1.5/2.5 Flash](https://aistudio.google.com/)
- **Database**: [PostgreSQL](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector)
- **Embedding Model**: [BGE-M3](https://huggingface.co/BAAI/bge-m3)
- **Reranker**: [BGE-Reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3)
- **Task Runner/CLI**: Custom `run.py` manager

## Project Structure

```text
backend/
├── api.py              # FastAPI main file & SSE streaming logic
├── requirements.txt    # Python dependencies
├── data/               # Raw university data (JSON format)
└── scripts/            # Core system logic
    ├── run.py          # Unified CLI entry point for all operations
    ├── db/             # Database connection and schema operations
    ├── embedder/       # The ingestion pipeline (Clean -> Chunk -> Embed -> Store)
    ├── retriever/      # Logic for Search, RAG, and the ReAct Agent
    └── generator/      # Gemini prompting and answer generation
```

## Getting Started

### 1. Environment Setup
Create a `.env` file in the `backend/` directory with the following keys:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/study_abroad_rag
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Install Dependencies
```bash
pip install -r backend/requirements.txt
```

### 3. Initialize Data & Database
Run the unified "init-all" command to set up the DB, create tables, and process all university data in `data/`:
```bash
python backend/scripts/run.py init-all
```

### 4. Start the API Server
```bash
uvicorn backend.api:app --reload --port 8000
```

## CLI Reference

The backend provides a powerful CLI via `run.py`. All commands should be run from the **project root**.

| Command | Description |
| :--- | :--- |
| `python backend/scripts/run.py setup` | Create the database if it doesn't exist. |
| `python backend/scripts/run.py import` | Re-build schema and re-import all JSON data. |
| `python backend/scripts/run.py rag "QUERY"` | Test the standard RAG pipeline in the terminal. |
| `python backend/scripts/run.py agent "QUERY"` | Test the Agentic RAG (steps & reasoning) in the terminal. |
| `python backend/scripts/run.py verify-vdb` | Check vector counts and index health. |

---
