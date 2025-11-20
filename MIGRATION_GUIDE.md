# Migration Guide: Qdrant to Supabase Vector Database

## Overview

This migration replaces Qdrant with Supabase's pgvector extension for vector storage and search. This simplifies the architecture by consolidating all data storage in Supabase.

## Why This Migration?

### Problems with the Old Architecture

1. **Dual Storage**: Data was split between Qdrant (vectors) and Supabase (metadata)
2. **Traceability Issues**: No explicit link between Qdrant vectors and Supabase source records
3. **User ID Mismatch**: Qdrant used hashed usernames while Supabase used UUIDs
4. **Sync Issues**: Deleting a source left orphaned vectors in Qdrant
5. **Deployment Complexity**: Required managing an additional Docker container

### Benefits of Supabase pgvector

✅ **Single Source of Truth**: All data in one place
✅ **Perfect Traceability**: Foreign key constraints link chunks to sources
✅ **Automatic Cleanup**: CASCADE deletion ensures consistency
✅ **Native Security**: Row Level Security (RLS) policies work seamlessly
✅ **Simpler Deployment**: One less Docker container to manage
✅ **ACID Guarantees**: PostgreSQL transaction safety
✅ **Production Ready**: Handles 1.6M+ embeddings efficiently

## What Changed

### Database Schema

**New Table**: `document_chunks`
```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,  -- Links to sources
    content TEXT,
    embedding vector(384),  -- pgvector type
    metadata JSONB,
    chunk_index INTEGER,
    created_at TIMESTAMP
);
```

### Code Changes

1. **Removed**:
   - `app/backend/db/qdrant_db.py`
   - `app/backend/services/user_manager.py`
   - `langchain-qdrant` dependency
   - `qdrant-client` dependency
   - Qdrant Docker container

2. **Added**:
   - `app/backend/db/supabase_vector_db.py` - New vector DB interface
   - `migrations/002_create_document_chunks_table.sql`
   - `migrations/003_add_audio_upload_type.sql`

3. **Modified**:
   - `main.py` - All endpoints now use SupabaseVectorDB
   - `docker-compose.yml` - Removed Qdrant service
   - `docker-compose.dev.yml` - Removed Qdrant service
   - `requirements.txt` - Removed Qdrant dependencies
   - `start.sh` - Removed Qdrant health checks
   - `dev.sh` - Removed Qdrant health checks

## Migration Steps

### 1. Run Database Migrations

Go to your Supabase project's SQL Editor and run:

```sql
-- 1. Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Run migration 002
-- (Copy content from app/backend/migrations/002_create_document_chunks_table.sql)

-- 3. Run migration 003
-- (Copy content from app/backend/migrations/003_add_audio_upload_type.sql)
```

### 2. Update Your Code

```bash
# Pull the latest changes
git pull origin <branch-name>

# Remove old Qdrant data (optional, but recommended)
docker-compose down -v

# Rebuild containers
docker-compose build

# Start with new architecture
docker-compose up -d
```

### 3. Re-process Existing Sources (If Applicable)

**Important**: Existing sources in the `sources` table will not have vectors in the new `document_chunks` table. You have two options:

**Option A**: Delete and re-add sources
- Users can delete their old sources via the UI
- Re-process them to generate new embeddings

**Option B**: Migration script (advanced)
- If you have a lot of data, you could write a script to:
  1. Fetch existing sources from Qdrant
  2. Re-process and insert into `document_chunks`
  3. This is not included as most deployments are in early stages

For most users, **Option A** is simpler and ensures clean data.

## Verification

### Check Migration Success

```bash
# 1. Check backend health
curl http://localhost:8000/health

# Should show:
# {
#   "status": "healthy",
#   "whisper": "loaded",
#   "ollama_api": "connected",
#   "supabase": "connected"
# }
```

### Test Vector Search

1. Process a new source (YouTube video or podcast)
2. Verify it appears in the sources list
3. Ask a question in chat to test vector search
4. Delete the source and verify chunks are also deleted (CASCADE)

## Rollback (If Needed)

If you need to rollback:

```bash
# 1. Checkout previous commit
git checkout <previous-commit-hash>

# 2. Rebuild containers
docker-compose down
docker-compose build
docker-compose up -d
```

**Note**: You'll lose any data added during the new system.

## Performance Considerations

### Indexing

The migration creates an HNSW index for fast vector search:

```sql
CREATE INDEX idx_document_chunks_embedding_hnsw
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops);
```

**Best Practices**:
- Keep your HNSW index in memory for best performance
- Monitor Supabase's compute resources
- Consider upgrading Supabase tier if handling large volumes

### Query Optimization

The new system uses a PostgreSQL function for similarity search:

```sql
CREATE FUNCTION match_document_chunks(
    query_embedding vector(384),
    match_count INT,
    filter_user_id UUID
) RETURNS TABLE (...)
```

This is optimized for:
- Fast similarity search using cosine distance
- User-filtered queries (RLS)
- Configurable result count

## New Features

### Source Statistics

The `/sources` endpoint now returns chunk counts:

```json
{
  "sources": [
    {
      "id": "uuid",
      "title": "Video Title",
      "type": "youtube",
      "chunkCount": 150
    }
  ]
}
```

### Automatic CASCADE Deletion

When a source is deleted, all associated chunks are automatically deleted through PostgreSQL CASCADE constraints. No orphaned data!

## Troubleshooting

### "pgvector extension not found"

Run in Supabase SQL Editor:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### "Source deleted but chunks remain"

This shouldn't happen with CASCADE constraints. If it does:
1. Check that migration 002 was run correctly
2. Verify foreign key constraints exist:
```sql
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f' AND conrelid = 'document_chunks'::regclass;
```

### Performance issues

1. Verify HNSW index exists:
```sql
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'document_chunks';
```

2. Monitor Supabase compute usage in dashboard
3. Consider upgrading Supabase tier

## Support

If you encounter issues:
1. Check the logs: `docker-compose logs backend`
2. Verify migrations ran successfully in Supabase
3. Test with the health endpoint
4. Review this migration guide

## Summary

This migration modernizes the YODA architecture by:
- ✅ Eliminating dual storage complexity
- ✅ Ensuring perfect data consistency
- ✅ Simplifying deployment
- ✅ Improving traceability
- ✅ Maintaining high performance

All while using battle-tested PostgreSQL with pgvector instead of a separate vector database.
