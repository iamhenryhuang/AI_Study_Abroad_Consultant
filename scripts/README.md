# AI Study Abroad Consultant Scripts

This directory contains scripts for database management, text vectorization (embedding), and RAG retrieval.

## Directory Structure

- `run.py`: **Unified entry point** for all operations.
- `db/`: Core logic for SQL database operations.
  - `ops.py`: DB setup, JSON data import, and SQL export.
  - `connection.py`: PostgreSQL connection management.
- `embedder/`: Logic for text chunking and vectorization.
  - `pipeline.py`: Main pipeline to chunk official descriptions.
  - `reddit_pipeline.py`: Pipeline for processing Reddit JSON data with larger chunks (1500 chars).
  - `vectorize.py`: Integration with **BGE-M3** model.
  - `store.py`: Handles upserting chunks with `source` labels ('official' or 'reddit').
  - `verifier.py`: Tool to verify Vector DB status (grouped by source).
- `retriever/`: Logic for RAG search.
  - `search.py`: Vector search with source column selection.
  - `rag_pipeline.py`: Orchestration with default `top_k=7` for hybrid results.
- `generator/`: Logic for LLM answer generation.
  - `gemini.py`: Adaptive prompt handling (Data-driven vs. Narrative-driven).

---

## Commands

Run these commands from the **project root directory**:

### 1. Database Basics
- **Initialize DB (Setup + Import JSON)**:
  ```bash
  python scripts/run.py init-all
  ```

### 2. Embedding Pipelines
- **Official Data Embedding**:
  ```bash
  python scripts/run.py embed
  ```
- **Reddit Data Embedding**:
  ```bash
  python scripts/run.py embed-reddit
  ```
- **Verify Vector Status**:
  ```bash
  python scripts/run.py verify-vdb
  ```

### 3. RAG Search & Generation
- **Execute Search Only**:
  ```bash
  python scripts/run.py search "your query"
  ```
- **Execute Full RAG**:
  ```bash
  python scripts/run.py rag "your query"
  ```

---

## Requirements
- PostgreSQL with `pgvector` extension.
- Local **BGE-M3** model path configured in `scripts/embedder/vectorize.py`.
- Dependencies listed in the root `requirements.txt`.
