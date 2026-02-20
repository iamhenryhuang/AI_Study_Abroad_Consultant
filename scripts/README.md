# AI Study Abroad Consultant Scripts

This directory contains scripts for database management, text vectorization (embedding), and RAG retrieval.

## Directory Structure

- `run.py`: **Unified entry point** for all operations.
- `db/`: Core logic for SQL database operations.
  - `ops.py`: DB setup, JSON data import, and SQL export.
  - `connection.py`: PostgreSQL connection management.
- `embedder/`: Logic for text chunking and vectorization.
  - `pipeline.py`: Main pipeline to chunk description text and store embeddings in `document_chunks`.
  - `vectorize.py`: Integration with **BGE-M3** model for high-quality embeddings.
  - `chunker.py`: Text splitting logic.
  - `verifier.py`: Tool to verify the status of the Vector DB.
- `retriever/`: Logic for RAG search.
  - `search.py`: Implementation of vector similarity search using pgvector.

---

## Commands

Run these commands from the **project root directory**:

### 1. Database Basics
- **Initialize DB (Setup + Import JSON)**:
  ```bash
  python scripts/run.py init-all
  ```
- **Verify SQL Data**:
  ```bash
  python scripts/run.py verify-db
  ```

### 2. Embedding Pipeline
- **Run Embedding Pipeline**:
  ```bash
  python scripts/run.py embed
  ```
- **Verify Vector DB Status**:
  ```bash
  python scripts/run.py verify-vdb
  ```

### 3. RAG Retrieval
- **Execute Search**:
  ```bash
  python scripts/run.py search "your query"
  ```
  *Example: `python scripts/run.py search "CMU MSCS research opportunities"`*

---

## Requirements
- PostgreSQL with `pgvector` extension.
- Local **BGE-M3** model path configured in `scripts/embedder/vectorize.py`.
- Dependencies listed in the root `requirements.txt`.
