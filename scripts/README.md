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
  - `multi_query.py`: Multi-Query expansion logic using LLM.
  - `rag_pipeline.py`: Orchestration of the full RAG flow (Search + Rerank + LLM).
- `generator/`: Logic for LLM answer generation.
  - `gemini.py`: Integration with **Gemini 2.5 Flash** for final answer synthesis.
- `evaluator/`: RAG quality evaluation (RAG Triad).
  - `rag_evaluation.py`: Uses Gemini as a judge to score Context Relevance, Faithfulness, and Answer Relevance.

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

### 3. RAG Search, Generation & Evaluation
- **Execute Search Only (Retrieval + Rerank)**:
  ```bash
  python scripts/run.py search "your query"
  ```
- **Execute Full RAG (Search + Answer)**:
  ```bash
  python scripts/run.py rag "your query"
  ```
- **Execute Full RAG with Quality Evaluation (RAG Triad)**:
  ```bash
  python scripts/run.py rag "your query" --eval
  ```
- **Execute Full RAG with Multi-Query Expansion**:
  ```bash
  python scripts/run.py rag "your query" --mq
  ```
  *Example: `python scripts/run.py rag "MIT CS admission requirements" --mq`*

---

## Requirements
- PostgreSQL with `pgvector` extension.
- Local **BGE-M3** model path configured in `scripts/embedder/vectorize.py`.
- Dependencies listed in the root `requirements.txt`.
