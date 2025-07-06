# YODA - Containerized Setup

YODA (Your Own Data Assistant) is now fully containerized! This setup includes:

- **Frontend**: Vue.js application served via nginx
- **Backend**: FastAPI application with Whisper transcription
- **Ollama API**: Wrapper service for Ollama LLM
- **Ollama**: Local LLM service for chat and summarization  
- **Qdrant**: Vector database for storing and searching transcripts

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 8GB of RAM (for running Ollama models)
- 10GB+ free disk space (for Docker images and models)

### 1. Clone and Setup

```bash
# Make the startup script executable
chmod +x start.sh
chmod +x stop.sh
```

### 2. Start Everything

```bash
# This will build and start all containers
./start.sh
```

The script will:
- Build all Docker images
- Start all services
- Wait for everything to be ready
- Optionally download default Ollama models
- Show you all the URLs and next steps

### 3. Access the Application

Once started, visit: **http://localhost**

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost | Main application interface |
| Backend API | http://localhost:8000 | FastAPI backend with Whisper |
| Ollama API | http://localhost:8001 | Ollama wrapper service |
| Qdrant | http://localhost:6333 | Vector database dashboard |
| Ollama | http://localhost:11434 | Direct Ollama access |

## Managing the Application

### Start/Stop

```bash
# Start everything
./start.sh

# Stop everything  
./stop.sh

# Restart specific service
docker-compose restart backend
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f ollama
docker-compose logs -f frontend
```

### Managing Ollama Models

```bash
# List installed models
docker exec ollama_service ollama list

# Pull a new model
docker exec ollama_service ollama pull llama3.2:3b

# Remove a model
docker exec ollama_service ollama rm llama3.2:1b
```

### Available Models

| Model | Size | Description |
|-------|------|-------------|
| llama3.2:1b | ~1.3GB | Lightweight, fast responses |
| llama3.2:3b | ~3GB | Better quality, slower responses |
| llama3:8b | ~4.7GB | High quality responses |
| codellama:7b | ~3.8GB | Specialized for code tasks |

## Data Persistence

Data is persisted in Docker volumes:

- **qdrant_data**: Vector database storage
- **ollama_data**: Downloaded models and Ollama data

To completely reset:

```bash
# Stop and remove everything including data
docker-compose down -v

# Then restart
./start.sh
```

## Development

### Local Development Mode

For development, you can run services individually:

```bash
# Start only infrastructure (Qdrant + Ollama)
docker-compose up -d qdrant ollama ollama-api

# Run backend locally
cd app/backend
python -m uvicorn main:app --reload

# Run frontend locally  
cd app/frontend
npm run dev
```

### Rebuilding After Changes

```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Rebuild everything
docker-compose build
docker-compose up -d
```

## Troubleshooting

### Common Issues

**"Ollama service unavailable"**
- Check if Ollama container is running: `docker-compose logs ollama`
- Restart Ollama: `docker-compose restart ollama`

**"No models available"**
- Pull a model: `docker exec ollama_service ollama pull llama3.2:1b`
- Check available models: `docker exec ollama_service ollama list`

**Frontend can't connect to backend**
- Check backend logs: `docker-compose logs backend`
- Verify backend is running: `curl http://localhost:8000/health`

**Out of disk space**
- Clean up Docker: `docker system prune -f`
- Remove unused images: `docker image prune -f`

### Performance Tips

1. **Memory**: Ensure Docker has at least 8GB RAM allocated
2. **CPU**: More CPU cores = faster transcription with Whisper
3. **Storage**: Use SSD for better performance
4. **Models**: Start with smaller models (1b/3b) and upgrade as needed

### Monitoring

```bash
# Check resource usage
docker stats

# Check service health
curl http://localhost:8000/health
curl http://localhost:6333/health
curl http://localhost:11434/api/version
```

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frontend  │───▶│   Backend   │───▶│   Qdrant    │
│  (Vue.js)   │    │  (FastAPI)  │    │ (VectorDB)  │
└─────────────┘    └─────────────┘    └─────────────┘
                           │
                           ▼
                   ┌─────────────┐    ┌─────────────┐
                   │ Ollama API  │───▶│   Ollama    │
                   │ (FastAPI)   │    │   (LLM)     │
                   └─────────────┘    └─────────────┘
```

## File Structure

```
.
├── docker-compose.yml          # Main orchestration
├── start.sh                    # Startup script
├── stop.sh                     # Stop script
├── app/
│   ├── frontend/
│   │   ├── Dockerfile
│   │   ├── nginx.conf
│   │   └── src/
│   ├── backend/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── services/
│   └── ollama-service/
│       ├── Dockerfile
│       ├── requirements.txt
│       └── ollama_service.py
```

## Security Notes

- This setup is for development/local use
- For production, configure proper authentication
- Use environment variables for sensitive configuration
- Consider using Docker secrets for API keys

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs [service]`
2. Verify all services are running: `docker-compose ps`
3. Check the troubleshooting section above
4. Restart problematic services: `docker-compose restart [service]`

---

Happy transcribing with YODA! 🎙️✨