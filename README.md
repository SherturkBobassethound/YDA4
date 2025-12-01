# YODA (Your Own Data Assistant)

YODA is a containerized application that allows you to ingest, transcribe, and query your own content (podcasts, YouTube videos) using local LLMs and vector search.

## 🏗 Architecture

The application is fully containerized and consists of:

- **Frontend**: Vue.js application served via nginx
- **Backend**: FastAPI application with Whisper transcription and direct Ollama integration
- **Ollama**: Local LLM service for chat and summarization
- **Supabase**: Authentication and Vector Database (pgvector)

```mermaid
graph LR
    Frontend[Frontend (Vue.js)] --> Backend[Backend (FastAPI)]
    Backend --> Supabase[(Supabase PGVector)]
    Backend --> Ollama[Ollama (LLM)]
```

## 🚀 Quick Start

### Prerequisites

- **Docker** and **Docker Compose** installed
- At least **8GB RAM** (for running Ollama models)
- **10GB+ free disk space**
- **Supabase Account** (Free tier works)

### 1. Supabase Setup

YODA uses Supabase for authentication and storing vector embeddings.

1.  **Create a Project**: Go to [database.new](https://database.new) and create a new project.
2.  **Get Credentials**:
    - Go to **Project Settings > API**.
    - Copy:
        - **Project URL** (`SUPABASE_URL`)
        - **anon/public key** (`SUPABASE_ANON_KEY`)
        - **service_role key** (`SUPABASE_SERVICE_KEY`) - *Keep secret!*
    - Scroll down to **JWT Settings** and copy **JWT Secret** (`SUPABASE_JWT_SECRET`).
3.  **Run Migrations**:
    - Go to **SQL Editor** in Supabase.
    - Copy the contents of `app/backend/migrations/001_create_sources_table.sql`.
    - Run the query to create the `sources` table.
    - Repeat for `app/backend/migrations/002_create_document_chunks_table.sql` and `003_add_audio_upload_type.sql`.

### 2. Environment Configuration

1.  Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
2.  Edit `.env` and fill in your Supabase credentials:
    ```env
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_ANON_KEY=your-anon-key
    SUPABASE_JWT_SECRET=your-jwt-secret
    SUPABASE_SERVICE_KEY=your-service-key
    ```
    *Note: `VITE_` variables are automatically populated from these.*

### 3. Start the Application

You can run the application in two modes:

**Option A: Production (Docker)**
Run the entire stack in Docker containers (recommended for deployment).
```bash
docker compose up --build -d
```
Access at **http://localhost**.

**Option B: Development (Local)**
Run services locally with hot-reloading (recommended for coding).
```bash
./dev.sh
```
Access at **http://localhost:5173**.

**Other Commands:**
- **Stop**: `docker compose down`
- **Logs**: `docker compose logs -f`
- **Clean**: `docker compose down -v` (removes all data)


### Troubleshooting Sources

If sources (podcasts/videos) are not appearing after processing:

1.  **Check `.env`**: Ensure `SUPABASE_URL` and keys are correct (not placeholders).
2.  **Verify Connection**: Run the diagnostic script:
    ```bash
    python3 test_supabase_connection.py
    ```
3.  **Check Logs**:
    ```bash
    docker-compose logs -f backend
    ```
    Look for "Saved source to database" or error messages.

## 📦 Data Persistence

- **Ollama Models**: Stored in `ollama_data` volume.
- **Vector Data**: Stored in your Supabase project (cloud).

To reset local data (models):
```bash
docker-compose down -v
```

## 📚 Migration Note (Qdrant to Supabase)

If you are migrating from an older version that used Qdrant:
1.  Run the Supabase migrations (`002` and `003`).
2.  Existing sources in Supabase will need to be re-processed to generate embeddings in the new `document_chunks` table. The easiest way is to delete them from the UI and add them again.
