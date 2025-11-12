#!/bin/bash

# Stop all local development services

set -e

# Colors
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${YELLOW}Stopping all development services...${NC}\n"

# Stop Docker services
echo -e "${YELLOW}Stopping Docker services...${NC}"
docker-compose -f docker-compose.dev.yml down
echo -e "${GREEN}✓ Docker services stopped${NC}"

# Kill any processes running on development ports
echo -e "${YELLOW}Cleaning up local processes...${NC}"

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ ! -z "$pid" ]; then
        kill -9 $pid 2>/dev/null || true
        echo -e "${GREEN}✓ Stopped process on port $port${NC}"
    fi
}

kill_port 8000  # Backend
kill_port 8001  # Ollama API
kill_port 5173  # Frontend

echo -e "\n${GREEN}✓ All services stopped${NC}\n"
