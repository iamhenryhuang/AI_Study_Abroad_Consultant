-- ============================================================
-- Study Abroad Consultant — Database Schema (v2)
-- 資料格式: school_info.json = { "url": "純文字", ... }
-- 學校透過 URL domain 自動識別
-- ============================================================

CREATE EXTENSION IF NOT EXISTS vector;

-- 先清除舊表（順序很重要，先刪有外鍵的子表）
DROP TABLE IF EXISTS document_chunks CASCADE;
DROP TABLE IF EXISTS web_pages CASCADE;
DROP TABLE IF EXISTS universities CASCADE;

-- ============================================================
-- 1. universities — 學校主表（從 URL domain 推斷）
-- ============================================================
CREATE TABLE universities (
    id          SERIAL PRIMARY KEY,
    school_id   VARCHAR(100) UNIQUE NOT NULL,   -- e.g. 'cmu', 'caltech'
    name        VARCHAR(255) NOT NULL,           -- e.g. 'Carnegie Mellon University'
    domain      VARCHAR(255),                    -- e.g. 'cmu.edu'
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. web_pages — 每個爬取的 URL 一筆（帶原始文字）
-- ============================================================
CREATE TABLE web_pages (
    id            SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    url           TEXT UNIQUE NOT NULL,          -- 原始 URL
    page_type     VARCHAR(100),                  -- 推斷的頁面類型 e.g. 'admissions', 'faq', 'checklist', 'general'
    raw_text      TEXT NOT NULL,                 -- 爬到的純文字
    char_count    INTEGER,                       -- 文字長度（方便 debug）
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_web_pages_university ON web_pages(university_id);
CREATE INDEX idx_web_pages_page_type  ON web_pages(page_type);

-- ============================================================
-- 3. document_chunks — 向量檢索主表（每個 chunk 一筆）
-- ============================================================
CREATE TABLE document_chunks (
    id            SERIAL PRIMARY KEY,
    university_id INTEGER REFERENCES universities(id) ON DELETE CASCADE,
    page_id       INTEGER REFERENCES web_pages(id) ON DELETE CASCADE,
    school_id     VARCHAR(100) NOT NULL,         -- 冗餘，加速過濾
    source_url    TEXT NOT NULL,                 -- 直接記錄原始 URL，方便回答時引用
    page_type     VARCHAR(100),                  -- 頁面類型，供 metadata filter 用
    chunk_index   INTEGER NOT NULL,              -- 同一 page_id 內的序號
    chunk_text    TEXT NOT NULL,
    embedding     vector(1024),                  -- BAAI/bge-m3 向量維度
    metadata      JSONB,                         -- 彈性擴充欄位（page_type, url, school_id 等）
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (page_id, chunk_index)
);

-- GIN index：加速 metadata JSONB 欄位查詢
CREATE INDEX idx_chunks_metadata
    ON document_chunks USING GIN (metadata);

-- HNSW index：加速向量相似度搜尋 (ANN)
CREATE INDEX idx_chunks_embedding
    ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- 加速 school_id/page_type 條件過濾
CREATE INDEX idx_chunks_school   ON document_chunks(school_id);
CREATE INDEX idx_chunks_pagetype ON document_chunks(page_type);
