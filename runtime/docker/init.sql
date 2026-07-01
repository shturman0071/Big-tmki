-- TMKI pgvector bootstrap (docker-compose)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS tmki_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    company_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    classification TEXT NOT NULL,
    payload JSONB NOT NULL,
    embedding vector(64) NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS tmki_chunks_project_idx ON tmki_chunks (company_id, project_id);
