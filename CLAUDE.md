# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YODA (Your Own Data Assistant) is a containerized application for transcribing and analyzing audio content from YouTube videos and podcasts using Whisper (transcription), Ollama (LLM), and Qdrant (vector storage). The system supports multi-user authentication via Supabase with Row-Level Security (RLS).

## Architecture

### Service Topology
- **Frontend**: Vue.js + TypeScript (Vite) on port 5173 (dev) / 80 (prod)
- **Backend API**: FastAPI with Whisper transcription on port 8000
- **Ollama API**: FastAPI wrapper for Ollama on port 8001
- **Qdrant**: Vector database on port 6333
- **Ollama**: LLM service on port 11434
- **Supabase**: External authentication and data storage service

### Key Design Patterns

**User Isolation**: Each user gets a dedicated Qdrant collection named `user_{user_id}` (see `services/user_manager.py:UserIdentifier.get_collection_name()`). Vector DB instances are created per-request using `get_user_vector_db()` in `main.py:33`.

**Authentication Flow**:
- Supabase handles user authentication and issues JWT tokens
- Backend validates tokens using JWT secret (see `auth.py:get_current_user()`)
- User's token is passed to Supabase client for RLS (see `services/supabase_client.py:get_user_supabase_client()`)
- ALL protected endpoints use `Depends(get_current_user)` dependency injection

**Data Pipeline**:
1. Audio acquisition (YouTube download via yt-dlp or podcast fetch via PodFetcher)
2. Whisper transcription (base model)
3. Text chunking via `TextSplitter` (500 char chunks, 50 char overlap)
4. Embedding generation (HuggingFace sentence-transformers/all-MiniLM-L6-v2)
5. Vector storage in user-specific Qdrant collection
6. Metadata storage in Supabase `sources` table

**Chat Context Enhancement**: The `/chat` endpoint performs vector similarity search to retrieve relevant chunks before sending to Ollama (see `main.py:325-383`).

## Development Commands

### Initial Setup

```bash
# 1. Configure Supabase (required)
cp .env.example .env
# Edit .env with your Supabase credentials from https://app.supabase.com/project/_/settings/api

# 2. Run database migration
# Go to Supabase SQL Editor and execute: app/backend/migrations/001_create_sources_table.sql
```

### Local Development (Recommended)

```bash
# Start services with hot-reload
./dev.sh
# OR
make dev

# This starts:
# - Qdrant & Ollama in Docker
# - Backend API with --reload at http://localhost:8000
# - Ollama API wrapper with --reload at http://localhost:8001
# - Frontend dev server at http://localhost:5173

# View logs
tail -f logs/backend.log
tail -f logs/ollama-api.log
tail -f logs/frontend.log

# Stop all services
./stop.sh
```

### Docker Production Mode

```bash
# Start all services in containers
./start.sh
# OR
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f ollama

# Stop
./stop.sh
# OR
docker-compose down
```

### Testing & Type Checking

```bash
# Frontend type checking
cd app/frontend
npm run type-check

# Frontend build
npm run build
```

### Backend Development

```bash
# Run backend locally (after starting Qdrant/Ollama with docker-compose -f docker-compose.dev.yml up -d)
cd app/backend
source ../../venv/bin/activate
QDRANT_URL=http://localhost:6333 OLLAMA_API_URL=http://localhost:8001 uvicorn main:app --reload --port 8000
```

### Ollama Model Management

```bash
# List installed models
docker exec ollama_service ollama list

# Pull a model
docker exec ollama_service ollama pull llama3.2:3b

# Remove a model
docker exec ollama_service ollama rm llama3.2:1b
```

## Critical Implementation Details

### Supabase Environment Variables

Four distinct values are required (commonly confused):
- `SUPABASE_URL`: Project URL
- `SUPABASE_ANON_KEY`: Public key for frontend
- `SUPABASE_JWT_SECRET`: For backend JWT verification (NOT the service key!)
- `SUPABASE_SERVICE_KEY`: For admin operations

The JWT secret is at the bottom of Project Settings > API page, distinct from service key.

### YouTube Download Fallback Strategy

`download_youtube_audio()` in `main.py:94-280` implements a 4-tier fallback strategy for handling YouTube's anti-bot measures:
1. Primary: bestaudio with specific format preferences
2. Fallback 1: More permissive format selection with Android user agent
3. Fallback 2: Download video and extract audio
4. Fallback 3: Lowest quality with maximum compatibility

### Authentication in API Calls

When working with Supabase data:
- Use `get_user_supabase_client(user['token'])` instead of global `supabase` client
- This ensures RLS policies are respected
- See pattern in `main.py:454`, `main.py:578`, `main.py:662`

### Vector DB Cleanup

Currently, deleting a source from Supabase does NOT delete associated vectors from Qdrant (see TODO at `main.py:735`). Vectors remain but are filtered via the `sources` table.

### Port Conflicts

Development mode requires ports 5173, 6333, 8000, 8001, 11434 to be available. Production mode requires ports 80, 6333, 8000, 8001, 11434.

## File Structure Notes

```
app/
├── backend/
│   ├── main.py              # FastAPI app with all endpoints
│   ├── auth.py              # JWT token verification
│   ├── services/
│   │   ├── pod_fetcher.py   # Podcast download logic (complex RSS/feed handling)
│   │   ├── text_splitter.py # Text chunking for embeddings
│   │   ├── user_manager.py  # User collection naming
│   │   └── supabase_client.py # Supabase client factory
│   ├── db/
│   │   └── qdrant_db.py     # Qdrant wrapper with LangChain integration
│   └── migrations/          # Supabase SQL migrations (run manually)
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── AuthModal.vue    # Supabase auth UI
│       │   ├── ChatApp.vue      # Main chat interface
│       │   ├── ProfileButton.vue # User profile dropdown
│       │   └── Sidebar.vue      # Source management
│       └── lib/
│           └── supabase.ts      # Supabase client initialization
└── ollama-service/
    └── ollama_service.py    # Thin FastAPI wrapper around Ollama API
```

## Common Workflows

### Adding a New Endpoint

1. Add route to `app/backend/main.py`
2. Use `user: dict = Depends(get_current_user)` for authentication
3. Get user's vector DB: `vector_db = get_user_vector_db(user['id'])`
4. For Supabase queries: `user_supabase = get_user_supabase_client(user['token'])`

### Modifying the Database Schema

1. Create new migration file in `app/backend/migrations/`
2. Apply manually via Supabase SQL Editor
3. Update RLS policies if needed
4. No ORM in use - all queries via Supabase client

### Adding a Frontend Component

1. Create `.vue` file in `app/frontend/src/components/`
2. Import in `App.vue` or parent component
3. Type checking: use `<script setup lang="ts">`
4. API calls should use `Authorization: Bearer ${token}` header

## Environment-Specific Behavior

**Development** (`ENVIRONMENT=development` or local dev mode):
- CORS allows all origins
- Services run with `--reload`
- Logs written to `logs/` directory
- JWT verification skipped if `SUPABASE_JWT_SECRET` not set (with warning)

**Production** (Docker compose):
- Strict CORS origins
- Services auto-restart
- All services health-checked
- JWT verification required

## Dependencies

**Backend Python**: FastAPI, Whisper (OpenAI), LangChain, Qdrant, HuggingFace Transformers, yt-dlp, Supabase, python-jose
**Frontend**: Vue 3, TypeScript, Vite, Supabase JS
**Infrastructure**: Docker, Docker Compose, Nginx (frontend prod server)

**Important**: NumPy constrained to <2 due to compatibility with Whisper/PyTorch dependencies (see `requirements.txt:7-8`).
