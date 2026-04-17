CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS regulation_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_key TEXT NOT NULL UNIQUE,
    content TEXT NOT NULL,
    embedding vector(1024),
    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_name TEXT NOT NULL,
    source_path TEXT NOT NULL,
    reg_type TEXT,
    region TEXT,
    typology TEXT,
    year INTEGER,
    chunk_index INTEGER NOT NULL DEFAULT 0,
    start_page INTEGER,
    end_page INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_embedding
    ON regulation_chunks
    USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_metadata_gin
    ON regulation_chunks
    USING gin (metadata);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_content_tsv
    ON regulation_chunks
    USING gin (content_tsv);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_source_name
    ON regulation_chunks (source_name);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_region
    ON regulation_chunks (region);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_typology
    ON regulation_chunks (typology);

CREATE INDEX IF NOT EXISTS idx_regulation_chunks_year
    ON regulation_chunks (year);

CREATE OR REPLACE FUNCTION set_regulation_chunks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_regulation_chunks_updated_at ON regulation_chunks;
CREATE TRIGGER trg_regulation_chunks_updated_at
BEFORE UPDATE ON regulation_chunks
FOR EACH ROW
EXECUTE FUNCTION set_regulation_chunks_updated_at();
