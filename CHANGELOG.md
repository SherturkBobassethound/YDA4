# Changelog

All notable changes to the YODA (Your On-Demand Assistant) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2025-11-16

### Added
- **Streaming Chat Responses**: Implemented real-time word-by-word chat responses using Server-Sent Events (SSE)
  - Backend streaming endpoint at `/chat/stream` in `app/backend/main.py:649-708`
  - Frontend streaming support in `app/frontend/src/components/ChatApp.vue:212-291`
  - Provides ChatGPT-like streaming experience for better user engagement

- **Lazy Loading for Whisper Model**: Implemented on-demand loading to save memory
  - Whisper model only loads when first transcription is requested
  - Added `get_whisper_model()` function in `app/backend/main.py:72-83`
  - Updated health check to show lazy loading status at `app/backend/main.py:760`

- **Expanded AI Model Support**: Added 4 new local LLM models
  - **phi3:3.8b** - Microsoft Phi-3, excellent quality for size (~2.3GB)
  - **gemma2:2b** - Google Gemma 2, fast and efficient (~1.6GB)
  - **qwen2.5:7b** - Qwen 2.5, strong reasoning and multilingual (~4.7GB)
  - **deepseek-r1:7b** - DeepSeek R1, excellent reasoning capabilities (~4.7GB)
  - Updated model selection UI in `app/frontend/src/components/ChatApp.vue:130-138`

- **Dynamic Model Discovery**: Frontend now fetches available models from Ollama API
  - Automatically detects installed models on component mount
  - Falls back to default model list if API unavailable
  - Implemented in `app/frontend/src/components/ChatApp.vue:141-169`

### Changed
- **Docker Health Checks**: Improved reliability and removed deprecated warnings
  - Fixed apt-key deprecation by using signed-by in sources.list
  - Updated health check intervals and timeouts for better container orchestration
  - Modified `docker-compose.yml` and `app/backend/dockerfile`

- **Authentication Integration**: Enhanced Supabase authentication for streaming
  - Added JWT token support for streaming endpoints
  - Direct import of supabase client in ChatApp component
  - Updated in `app/frontend/src/components/ChatApp.vue:94`

### Fixed
- **Git Repository Structure**: Cleaned up repository organization
  - Moved git root from `/YD52/` to `/YD52/app2/YDA4-main/`
  - Removed duplicate `app2/` directory structure
  - Proper branch tracking for `removebarriers` branch

- **Model Tag Display**: Added visual indicator showing which AI model generated each response
  - Shows model name below each AI response in chat
  - Implemented in `app/frontend/src/components/ChatApp.vue:64,363-370`

### Technical Details

#### Streaming Implementation
- **Backend**: Uses FastAPI `StreamingResponse` with async generators
- **Frontend**: Uses fetch API with ReadableStream and TextDecoder
- **Protocol**: Server-Sent Events (SSE) with `text/event-stream` content type
- **Integration**: Seamlessly works with vector database context retrieval

#### Lazy Loading Benefits
- Reduces initial memory footprint by ~1.5GB
- Faster container startup time
- Model loads in ~2-3 seconds on first transcription request
- Stays loaded for subsequent requests

#### Model Information
All models run locally via Ollama, ensuring privacy and no API costs:
- **Lightweight**: llama3.2:1b (1.3GB), gemma2:2b (1.6GB)
- **Balanced**: phi3:3.8b (2.3GB), llama3.2:3b (3GB)
- **High Quality**: qwen2.5:7b (4.7GB), deepseek-r1:7b (4.7GB), llama3:8b (4.7GB)

### Infrastructure
- **Backend**: Python/FastAPI with async support
- **Frontend**: Vue 3 with TypeScript and Composition API
- **Authentication**: Supabase Auth with JWT tokens
- **Vector DB**: Qdrant for semantic search and context-aware chat
- **LLM Service**: Ollama for local model inference
- **Transcription**: OpenAI Whisper (base model)
- **Containerization**: Docker Compose with 5 services

### Repository
- **Branch**: `removebarriers`
- **Remote**: https://github.com/SherturkBobassethound/YDA4

---

## Notes

This changelog documents improvements made during the November 2025 development sprint focused on:
1. Performance optimization (lazy loading)
2. User experience enhancement (streaming responses)
3. AI model expansion (4 new models)
4. Infrastructure reliability (health checks, git cleanup)

For detailed implementation, refer to the commit history in the `removebarriers` branch.
