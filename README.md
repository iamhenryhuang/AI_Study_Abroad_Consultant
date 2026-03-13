# Study Abroad RAG: North America CS Master's Consultant

A RAG-based tool built to simplify the search for North American CS master's programs. It scrapes official university pages, indexes them in a vector database, and uses an LLM agent to provide context-aware answers about admission requirements and application strategies.

---

## Operations & CLI Commands

All Python commands should be run from the **project root**.

### 1. Database (SQL) Operations
Manage the PostgreSQL schema and traditional data:
- **`python backend/scripts/run.py setup`**: Check connection and create the `study_abroad` database if it doesn't exist.
- **`python backend/scripts/run.py verify-db`**: Verify that the universities and web pages have been correctly imported into SQL.
- **`python backend/scripts/run.py export`**: Export a data summary to `db/exported_data.sql`.

### 2. Embedding & Vector Pipeline
Prepare and index data for semantic search:
- **`python backend/scripts/run.py import`**: Build schema + Chunk text + Embed + Store everything in Postgres.
- **`python backend/scripts/run.py embed`**: Specifically runs the chunking and embedding pipeline for existing records.
- **`python backend/scripts/run.py verify-vdb`**: Check the vector store status (chunk counts, vector dimensions, and HNSW index).

### 3. RAG & Search Operations
Test the retrieval and generation logic in the terminal:
- **Vector Search (No LLM)**:
  - `python backend/scripts/run.py search "MSCS admission requirements"`
  - `python backend/scripts/run.py search "funding" --school caltech`
- **Standard RAG (Retrieval + LLM)**:
  - `python backend/scripts/run.py rag "What are the requirements for CMU?"`
  - `python backend/scripts/run.py rag "Compare deadlines" --mq` (Uses **Multi-Query** to expand search)
  - `python backend/scripts/run.py rag "GPA reqs" --school ucla` (Filters by specific school)

### 4. Agentic RAG (Advanced Reasoning)
Uses a ReAct loop to solve complex queries that require multiple steps:
- **`python backend/scripts/run.py agent "Compare Stanford and MIT deadlines"`**
- **`python backend/scripts/run.py agent "Which school has best AI faculty?" --max-steps 10`**

### 5. Professor Profiling
Fetch research data and embed it directly:
- **`python -m backend.scripts.professor_fetcher.run_fetch --name "Andrew Ng" --school "Stanford" --embed`**

---

## Running the Application

### One-Time Initialization
If this is your first time setting up, run this to handle both DB setup and data import:
```bash
python backend/scripts/run.py init-all
```

### Starting the Services
You need two terminals running simultaneously.

#### **Backend (FastAPI)**
```bash
# Install dependencies first
pip install -r backend/requirements.txt

# Start the uvicorn server
uvicorn backend.api:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/health`

#### **Frontend (React)**
```bash
cd frontend
npm install
npm run dev
```
- Local URL: `http://localhost:5173`

---

## Project Structure

```text
├── backend/                # FastAPI application
│   ├── api.py              # API entry point & SSE logic
│   ├── data/               # University JSON dumps
│   ├── scripts/            # Core logic
│   │   ├── db/             # SQL operations
│   │   ├── embedder/       # Chunking & Embedding
│   │   ├── retriever/      # Search, RAG, and Agent logic
│   │   └── run.py          # Unified CLI Entry point
│   └── requirements.txt    # Python dependencies
├── db/                     # Database schema & init scripts
└── frontend/               # React application (Vite + TS)
```

---

## Technical Highlights

- **Gemini 2.5 Flash**: Backend LLM for high-speed reasoning.
- **BGE-M3 & Reranker**: State-of-the-art embedding and cross-encoder models.
- **pgvector + HNSW**: Efficient vector storage and retrieval within PostgreSQL.
- **FastAPI SSE**: Real-time streaming of the Agent's "thinking" process to the UI.
- **Dynamic Chunking**: Context-aware text splitting (FAQ, Admissions, Checklists).

---
