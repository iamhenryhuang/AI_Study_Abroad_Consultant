# Study Abroad RAG: North America CS Consultant

> **Smart, Agent-based RAG system for North American CS Master's Admissions.**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC.svg)](https://tailwindcss.com/)

---

## Overview

Study Abroad RAG is an intelligent advisory tool designed to simplify the complex process of researching North American CS Master's programs. Instead of manually scouring hundreds of university pages, users can ask our **Agentic RAG** system specific questions about admission requirements, funding, faculty, and deadlines.

The system doesn't just "search" — it **reasons**, **compares**, and **cites** its sources accurately.

### Key Features
- **Agentic Reasoning**: Uses a ReAct loop to solve multi-faceted queries (e.g., "Compare the GRE requirements of Stanford vs. CMU").
- **Real-Time Thinking**: Watch the AI work as it plans its search, executes steps, and synthesizes the answer.
- **High Precision**: Powered by **BGE-M3** embeddings and a **Cross-Encoder Reranker** for the best document retrieval.
- **Contextual Chunking**: Proprietary chunking strategy that preserves metadata and FAQ structures.
- **Verified Sources**: Every claim includes a direct source URL to the university's official page.

---

## Architecture

```text
.
├── backend/                # FastAPI, Vector DB logic, Gemini Agent
│   ├── api.py              # API server with SSE support
│   ├── scripts/            # Core RAG & Ingestion logic
│   └── data/               # University JSON dumps (Scraped data)
├── frontend/               # React + Tailwind v4 + Vite
│   ├── src/components/     # Modern UI components
│   └── src/hooks/          # Real-time streaming hooks
└── db/                     # SQL schema & PostgreSQL migrations
```

---

## Quick Start

### 1. Prerequesites
- **Python 3.10+**
- **Node.js 18+**
- **PostgreSQL** with the [pgvector](https://github.com/pgvector/pgvector) extension.

### 2. Initialization (The Easy Way)
From the **root directory**, run the one-command setup:
```bash
# Setup DB and import all data (approx. 2-5 mins)
python backend/scripts/run.py init-all
```

### 3. Start Services
Open two terminals:

**Terminal A: Backend**
```bash
pip install -r backend/requirements.txt
uvicorn backend.api:app --reload --port 8000
```

**Terminal B: Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## CLI Power Tools

Manage the entire pipeline directly from your terminal using `backend/scripts/run.py`:

- **`search "QUERY"`**: Pure vector search results.
- **`rag "QUERY"`**: Standard Retrieval-Augmented Generation.
- **`agent "QUERY"`**: The advanced Agentic RAG ReAct loop.
- **`verify-vdb`**: Check the pulse of your vector database.

---

## Documentation
For detailed information on specific modules, please refer to:
- [Backend Documentation](backend/README.md)
- [Frontend Documentation](frontend/README.md)

---
