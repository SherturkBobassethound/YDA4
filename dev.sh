#!/bin/bash

# Local Development Startup Script
# Starts all services for local development with hot-reload

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}YODA Local Development Setup${NC}"
echo -e "${BLUE}================================${NC}\n"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
port_in_use() {
    lsof -i :"$1" >/dev/null 2>&1
}

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit
}

trap cleanup SIGINT SIGTERM

# Check required commands
echo -e "${YELLOW}Checking dependencies...${NC}"
required_commands=("docker" "docker-compose" "python3" "node" "npm")
missing_commands=()

for cmd in "${required_commands[@]}"; do
    if ! command_exists "$cmd"; then
        missing_commands+=("$cmd")
    fi
done

if [ ${#missing_commands[@]} -ne 0 ]; then
    echo -e "${RED}Error: Missing required commands: ${missing_commands[*]}${NC}"
    echo "Please install them before continuing."
    exit 1
fi

echo -e "${GREEN}✓ All dependencies found${NC}\n"

# Check if .env exists, if not copy from .env.local
if [ ! -f .env ]; then
    if [ -f .env.local ]; then
        echo -e "${YELLOW}Copying .env.local to .env...${NC}"
        cp .env.local .env
        echo -e "${GREEN}✓ .env created${NC}\n"
    else
        echo -e "${YELLOW}Warning: No .env file found. Services may use default values.${NC}\n"
    fi
fi

# Start Docker services (Qdrant and Ollama)
echo -e "${BLUE}Starting Docker services (Qdrant & Ollama)...${NC}"
docker-compose -f docker-compose.dev.yml up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for Qdrant to be ready...${NC}"
until curl -f http://localhost:6333/health >/dev/null 2>&1; do
    sleep 2
done
echo -e "${GREEN}✓ Qdrant is ready${NC}"

echo -e "${YELLOW}Waiting for Ollama to be ready...${NC}"
until curl -f http://localhost:11434/api/version >/dev/null 2>&1; do
    sleep 2
done
echo -e "${GREEN}✓ Ollama is ready${NC}\n"

# Check if Ollama models are installed
echo -e "${YELLOW}Checking Ollama models...${NC}"
if docker exec ollama_service_dev ollama list | grep -q "llama3.2:1b"; then
    echo -e "${GREEN}✓ Ollama models found${NC}\n"
else
    echo -e "${YELLOW}Installing default Ollama model (llama3.2:1b)...${NC}"
    echo -e "${YELLOW}This may take several minutes...${NC}"
    docker exec ollama_service_dev ollama pull llama3.2:1b
    echo -e "${GREEN}✓ Model installed${NC}\n"
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}\n"
fi

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies for backend
echo -e "${YELLOW}Installing backend dependencies...${NC}"
cd app/backend
if [ ! -f ".deps_installed" ] || [ requirements.txt -nt .deps_installed ]; then
    pip install -q -r requirements.txt
    touch .deps_installed
    echo -e "${GREEN}✓ Backend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Backend dependencies up to date${NC}"
fi
cd ../..

# Install Python dependencies for ollama-service
echo -e "${YELLOW}Installing ollama-service dependencies...${NC}"
cd app/ollama-service
if [ ! -f ".deps_installed" ] || [ requirements.txt -nt .deps_installed ]; then
    pip install -q -r requirements.txt
    touch .deps_installed
    echo -e "${GREEN}✓ Ollama-service dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Ollama-service dependencies up to date${NC}"
fi
cd ../..

# Install frontend dependencies
echo -e "${YELLOW}Installing frontend dependencies...${NC}"
cd app/frontend
if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✓ Frontend dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Frontend dependencies up to date${NC}"
fi
cd ../..

echo -e "\n${BLUE}================================${NC}"
echo -e "${BLUE}Starting Development Services${NC}"
echo -e "${BLUE}================================${NC}\n"

# Create log directory
mkdir -p logs

# Start Ollama API service
echo -e "${GREEN}Starting Ollama API (port 8001)...${NC}"
cd app/ollama-service
OLLAMA_BASE_URL=http://localhost:11434 uvicorn ollama_service:app --reload --host 0.0.0.0 --port 8001 > ../../logs/ollama-api.log 2>&1 &
OLLAMA_API_PID=$!
cd ../..

# Wait for ollama-api to start
sleep 3

# Start Backend API
echo -e "${GREEN}Starting Backend API (port 8000)...${NC}"
cd app/backend
QDRANT_URL=http://localhost:6333 OLLAMA_API_URL=http://localhost:8001 uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
cd ../..

# Wait for backend to start
sleep 3

# Start Frontend
echo -e "${GREEN}Starting Frontend (port 5173)...${NC}"
cd app/frontend
VITE_API_BASE_URL=http://localhost:8000 VITE_OLLAMA_API_URL=http://localhost:8001 npm run dev > ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
cd ../..

echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}✓ All services started!${NC}"
echo -e "${BLUE}================================${NC}\n"

echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  Frontend:    ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend API: ${GREEN}http://localhost:8000${NC}"
echo -e "  Ollama API:  ${GREEN}http://localhost:8001${NC}"
echo -e "  Qdrant:      ${GREEN}http://localhost:6333${NC}"
echo -e "  Ollama:      ${GREEN}http://localhost:11434${NC}\n"

echo -e "${YELLOW}Logs:${NC}"
echo -e "  Backend:     ${GREEN}tail -f logs/backend.log${NC}"
echo -e "  Ollama API:  ${GREEN}tail -f logs/ollama-api.log${NC}"
echo -e "  Frontend:    ${GREEN}tail -f logs/frontend.log${NC}\n"

echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"

# Wait for all background jobs
wait
