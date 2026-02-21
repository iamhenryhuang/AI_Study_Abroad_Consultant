

-- 1. Universities Table
CREATE TABLE IF NOT EXISTS universities (
    id SERIAL PRIMARY KEY,
    school_id VARCHAR(100) UNIQUE NOT NULL,
    university VARCHAR(255) NOT NULL,
    program VARCHAR(255) NOT NULL,
    official_link TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Requirements Table
CREATE TABLE IF NOT EXISTS requirements (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    toefl_min_total INTEGER,
    toefl_required BOOLEAN DEFAULT FALSE,
    toefl_notes TEXT,
    ielts_min_total DECIMAL(3,1),
    ielts_required BOOLEAN DEFAULT FALSE,
    ielts_notes TEXT,
    gre_status VARCHAR(50),
    gre_notes TEXT,
    minimum_gpa DECIMAL(3,2),
    recommendation_letters INTEGER,
    interview_required VARCHAR(100) DEFAULT 'false'
);

-- 3. Deadlines Table
CREATE TABLE IF NOT EXISTS deadlines (
    id SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    fall_intake DATE,
    spring_intake VARCHAR(100) -- Using VARCHAR as it might be "Not Available"
);

-- 4. Document Chunks Table (for RAG / vector search)
CREATE TABLE IF NOT EXISTS document_chunks (
    id            SERIAL PRIMARY KEY,
    school_id     VARCHAR(100) NOT NULL,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    chunk_text    TEXT NOT NULL,
    embedding     vector(1024),
    -- 結構化 metadata：存入數字/日期欄位，供 hybrid query WHERE 過濾
    metadata      JSONB,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (school_id, chunk_index)
);

-- GIN index：加速 metadata JSONB 欄位的條件查詢
CREATE INDEX IF NOT EXISTS idx_chunks_metadata
    ON document_chunks USING GIN (metadata);

-- HNSW index：加速向量相似度搜尋 (ANN)
-- m: 每個節點的最大連接數 (預設 16), ef_construction: 建立索引時的搜尋範圍 (預設 64)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
