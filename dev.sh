#!/bin/bash

# Local Development Startup Script
# Starts all services for local development with hot-reload

# Don't exit on error - we want to see what's happening
set +e

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

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    exit
}

trap cleanup SIGINT SIGTERM

# Check required commands (without Docker)
echo -e "${YELLOW}Checking dependencies...${NC}"
required_commands=("python3" "node" "npm")
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

# Check if Ollama is already running (native or Docker)
echo -e "${YELLOW}Checking Ollama...${NC}"
if curl -s http://localhost:11434/api/version >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Ollama is already running${NC}\n"
else
    # Ollama is not running, try to start it with Docker if available
    if command_exists "docker" && docker info >/dev/null 2>&1; then
        echo -e "${YELLOW}Starting Ollama in Docker...${NC}"
        docker-compose up -d ollama

        # Wait for Ollama to be ready
        RETRY_COUNT=0
        MAX_RETRIES=30
        until curl -s http://localhost:11434/api/version >/dev/null 2>&1; do
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
                echo -e "${RED}✗ Ollama failed to start${NC}"
                echo "Please start Ollama manually or check Docker logs"
                exit 1
            fi
            sleep 2
        done
        echo -e "${GREEN}✓ Ollama started in Docker${NC}\n"

        # Check if models are installed
        echo -e "${YELLOW}Checking Ollama models...${NC}"
        if docker exec ollama_service ollama list 2>/dev/null | grep -q "llama3.2:1b"; then
            echo -e "${GREEN}✓ Ollama models found${NC}\n"
        else
            echo -e "${YELLOW}Installing default Ollama model (llama3.2:1b)...${NC}"
            docker exec ollama_service ollama pull llama3.2:1b
            echo -e "${GREEN}✓ Model installed${NC}\n"
        fi
    else
        echo -e "${RED}Error: Ollama is not running and Docker is not available${NC}"
        echo -e "${YELLOW}Please either:${NC}"
        echo -e "  1. Install and start Ollama: ${GREEN}https://ollama.ai${NC}"
        echo -e "  2. Or install Docker and try again"
        exit 1
    fi
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

# Start Backend API
echo -e "${GREEN}Starting Backend API (port 8000)...${NC}"
cd app/backend || exit 1
OLLAMA_BASE_URL=http://localhost:11434 uvicorn main:app --reload --host 0.0.0.0 --port 8000 >> ../../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo -e "${GREEN}Backend PID: $BACKEND_PID${NC}"
cd ../.. || exit 1

# Wait for backend to start
echo -e "${YELLOW}Waiting for backend to start...${NC}"
sleep 3

# Verify backend is running
if ! curl -s http://localhost:8000/health >/dev/null 2>&1; then
    echo -e "${YELLOW}Backend is starting (may take a moment)...${NC}"
    sleep 2
fi

# Start Frontend
echo -e "${GREEN}Starting Frontend (port 5173)...${NC}"
cd app/frontend || exit 1
VITE_API_BASE_URL=http://localhost:8000 npm run dev >> ../../logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend PID: $FRONTEND_PID${NC}"
cd ../.. || exit 1

# Wait a moment for frontend to start
sleep 2

# Ensure log files exist
touch logs/backend.log logs/frontend.log 2>/dev/null || true

echo -e "\n${BLUE}================================${NC}"
echo -e "${GREEN}✓ All services started!${NC}"
echo -e "${BLUE}================================${NC}\n"

echo -e "${YELLOW}Service URLs:${NC}"
echo -e "  Frontend:    ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend API: ${GREEN}http://localhost:8000${NC}"
echo -e "  Ollama:      ${GREEN}http://localhost:11434${NC}\n"

echo -e "${YELLOW}Viewing combined logs (Ctrl+C to stop all services):${NC}\n"
echo -e "${YELLOW}----------------------------------------${NC}\n"

# Enhanced cleanup function
cleanup() {
    echo -e "\n\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    # Kill any tail processes
    pkill -P $$ tail 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Show initial log content if available
echo -e "${BLUE}=== Checking services... ===${NC}"
if [ -s logs/backend.log ]; then
    echo -e "${BLUE}Backend log found (showing last 5 lines):${NC}"
    tail -n 5 logs/backend.log
    echo ""
else
    echo -e "${YELLOW}Backend log is empty (service may still be starting)${NC}"
fi

if [ -s logs/frontend.log ]; then
    echo -e "${GREEN}Frontend log found (showing last 5 lines):${NC}"
    tail -n 5 logs/frontend.log
    echo ""
else
    echo -e "${YELLOW}Frontend log is empty (service may still be starting)${NC}"
fi
echo ""

echo -e "${YELLOW}=== Following logs (live updates) ===${NC}"
echo -e "${YELLOW}If you see a blank screen, the services are starting...${NC}"
echo -e "${YELLOW}Logs will appear here as services generate output.${NC}\n"
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}\n"
echo -e "${YELLOW}----------------------------------------${NC}\n"

# Tail both log files - tail will show which file each line comes from
# The '==> filename <==' headers will show which service each line is from
tail -f logs/backend.log logs/frontend.log
