-- Create tables for Study Abroad Consultant
DROP TABLE IF EXISTS deadlines;
DROP TABLE IF EXISTS requirements;
DROP TABLE IF EXISTS universities;

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
