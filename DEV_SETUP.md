# Local Development Setup

This guide explains how to run all services locally outside of Docker for faster development cycles with hot-reload.

## Architecture

**In Docker (dependencies):**
- Qdrant (Vector Database) - port 6333
- Ollama (LLM Service) - port 11434

**Running Locally (hot-reload):**
- Backend API (FastAPI) - port 8000
- Ollama API Service (FastAPI) - port 8001
- Frontend (Vue/Vite) - port 5173

## Prerequisites

Make sure you have the following installed:

- **Docker & Docker Compose** - For Qdrant and Ollama
- **Python 3.9+** - For backend services
- **Node.js 18+** - For frontend
- **npm or yarn** - For frontend dependencies

## Quick Start

### 1. Start All Services

```bash
./dev.sh
```

This script will:
1. Start Qdrant and Ollama in Docker
2. Create Python virtual environment if needed
3. Install all Python dependencies
4. Install frontend dependencies
5. Start all local services with hot-reload

### 2. Access Services

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Backend API Docs**: http://localhost:8000/docs
- **Ollama API**: http://localhost:8001
- **Qdrant Dashboard**: http://localhost:6333/dashboard

### 3. Stop All Services

```bash
./dev-stop.sh
```

Or press `Ctrl+C` in the terminal running `dev.sh`.

## Manual Setup (Alternative)

If you prefer to start services manually:

### 1. Start Docker Services

```bash
docker-compose -f docker-compose.dev.yml up -d
```

### 2. Setup Python Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install backend dependencies
cd app/backend
pip install -r requirements.txt
cd ../..

# Install ollama-service dependencies
cd app/ollama-service
pip install -r requirements.txt
cd ../..
```

### 3. Start Backend Services

In separate terminals (with venv activated):

```bash
# Terminal 1: Ollama API Service
cd app/ollama-service
OLLAMA_BASE_URL=http://localhost:11434 uvicorn ollama_service:app --reload --host 0.0.0.0 --port 8001
```

```bash
# Terminal 2: Backend API
cd app/backend
QDRANT_URL=http://localhost:6333 OLLAMA_API_URL=http://localhost:8001 uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start Frontend

```bash
# Terminal 3: Frontend
cd app/frontend
npm install  # First time only
VITE_API_BASE_URL=http://localhost:8000 VITE_OLLAMA_API_URL=http://localhost:8001 npm run dev
```

## Development Workflow

### Making Changes

All services have hot-reload enabled:

- **Backend/Ollama API**: Changes to `.py` files automatically restart the server
- **Frontend**: Changes to `.vue`, `.ts`, `.js` files automatically refresh the browser

### Viewing Logs

Logs are written to the `logs/` directory:

```bash
# Watch backend logs
tail -f logs/backend.log

# Watch ollama-api logs
tail -f logs/ollama-api.log

# Watch frontend logs
tail -f logs/frontend.log
```

### Installing New Dependencies

**Python (Backend/Ollama-API):**
```bash
source venv/bin/activate
cd app/backend  # or app/ollama-service
pip install new-package
pip freeze > requirements.txt
```

**JavaScript (Frontend):**
```bash
cd app/frontend
npm install new-package
```

### Managing Ollama Models

```bash
# List installed models
docker exec ollama_service_dev ollama list

# Pull a new model
docker exec ollama_service_dev ollama pull llama3.2:3b

# Remove a model
docker exec ollama_service_dev ollama rm llama3.2:1b
```

## Environment Variables

Create a `.env` file in the root directory (copy from `.env.local`):

```bash
cp .env.local .env
```

Edit as needed for your environment.

## Troubleshooting

### Port Already in Use

If you get "port already in use" errors:

```bash
# Check what's using the port
lsof -i :8000  # or 8001, 5173, etc.

# Kill the process
kill -9 <PID>

# Or use the stop script
./dev-stop.sh
```

### Docker Services Won't Start

```bash
# Check Docker status
docker ps

# View logs
docker-compose -f docker-compose.dev.yml logs

# Restart services
docker-compose -f docker-compose.dev.yml restart
```

### Python Dependencies Issues

```bash
# Clear and reinstall
rm -rf venv
python3 -m venv venv
source venv/bin/activate
cd app/backend && pip install -r requirements.txt
cd ../ollama-service && pip install -r requirements.txt
```

### Frontend Not Loading

```bash
# Clear node_modules and reinstall
cd app/frontend
rm -rf node_modules package-lock.json
npm install
```

### Qdrant Data Issues

```bash
# Clear Qdrant data (WARNING: This deletes all data)
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up -d
```

## Performance Tips

1. **Use SSD**: Ensure your project is on an SSD for faster dependency installation and rebuilds
2. **Increase Docker Resources**: Allocate more CPU/RAM to Docker if services are slow
3. **Disable Unused Services**: Comment out services you're not actively developing in the startup script

## Switching Back to Docker

To switch back to full Docker setup:

```bash
# Stop dev services
./dev-stop.sh

# Start production Docker setup
docker-compose up -d
```

## VS Code Integration

Add these to your `.vscode/launch.json` for debugging:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Backend API",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["main:app", "--reload", "--port", "8000"],
      "cwd": "${workspaceFolder}/app/backend",
      "env": {
        "QDRANT_URL": "http://localhost:6333",
        "OLLAMA_API_URL": "http://localhost:8001"
      }
    },
    {
      "name": "Ollama API",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["ollama_service:app", "--reload", "--port", "8001"],
      "cwd": "${workspaceFolder}/app/ollama-service",
      "env": {
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  ]
}
```

## Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Vue 3 Documentation](https://vuejs.org/)
- [Vite Documentation](https://vitejs.dev/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Ollama Documentation](https://ollama.ai/docs/)
