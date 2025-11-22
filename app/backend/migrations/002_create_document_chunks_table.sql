-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create document_chunks table for storing document embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(384),  -- 384 dimensions for sentence-transformers/all-MiniLM-L6-v2
    metadata JSONB DEFAULT '{}'::jsonb,
    chunk_index INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create HNSW index for fast vector similarity search using cosine distance
-- HNSW (Hierarchical Navigable Small World) is optimal for high-dimensional vectors
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);

-- Create index for faster queries by user_id
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id
    ON document_chunks(user_id);

-- Create index for faster queries by source_id
CREATE INDEX IF NOT EXISTS idx_document_chunks_source_id
    ON document_chunks(source_id);

-- Create composite index for user_id and created_at (for ordering)
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_created
    ON document_chunks(user_id, created_at DESC);

-- Enable Row Level Security (RLS)
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;

-- Create policy: Users can only see their own document chunks
CREATE POLICY "Users can view their own document chunks"
    ON document_chunks FOR SELECT
    USING (auth.uid() = user_id);

-- Create policy: Users can insert their own document chunks
CREATE POLICY "Users can insert their own document chunks"
    ON document_chunks FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Create policy: Users can delete their own document chunks
CREATE POLICY "Users can delete their own document chunks"
    ON document_chunks FOR DELETE
    USING (auth.uid() = user_id);

-- Create a function to get similar documents using vector similarity
-- This function will be used for semantic search
CREATE OR REPLACE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_count INT DEFAULT 5,
    filter_user_id UUID DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        document_chunks.id,
        document_chunks.content,
        document_chunks.metadata,
        1 - (document_chunks.embedding <=> query_embedding) AS similarity
    FROM document_chunks
    WHERE
        (filter_user_id IS NULL OR document_chunks.user_id = filter_user_id)
        AND (filter_user_id IS NULL OR auth.uid() = document_chunks.user_id)
    ORDER BY document_chunks.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
