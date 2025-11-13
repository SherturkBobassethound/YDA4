#!/bin/bash

# System Requirements Check for YODA Development

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}YODA System Requirements Check${NC}"
echo -e "${BLUE}================================${NC}\n"

all_good=true

# Check commands
echo -e "${YELLOW}Checking installed commands...${NC}"
commands=("docker" "docker-compose" "python3" "node" "npm" "curl")

for cmd in "${commands[@]}"; do
    if command -v "$cmd" >/dev/null 2>&1; then
        version=$(eval "$cmd --version 2>&1 | head -1")
        echo -e "  ${GREEN}✓${NC} $cmd - $version"
    else
        echo -e "  ${RED}✗${NC} $cmd - NOT FOUND"
        all_good=false
    fi
done

# Check Docker daemon
echo -e "\n${YELLOW}Checking Docker daemon...${NC}"
if docker info >/dev/null 2>&1; then
    echo -e "  ${GREEN}✓${NC} Docker daemon is running"
else
    echo -e "  ${RED}✗${NC} Docker daemon is not running"
    all_good=false
fi

# Check ports
echo -e "\n${YELLOW}Checking required ports...${NC}"
ports=(5173 6333 8000 8001 11434)

for port in "${ports[@]}"; do
    if lsof -i :$port >/dev/null 2>&1; then
        process=$(lsof -i :$port | tail -1 | awk '{print $1}')
        echo -e "  ${YELLOW}⚠${NC}  Port $port is in use by $process"
    else
        echo -e "  ${GREEN}✓${NC} Port $port is available"
    fi
done

# Check Python version
echo -e "\n${YELLOW}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
if [ ! -z "$python_version" ]; then
    major=$(echo $python_version | cut -d. -f1)
    minor=$(echo $python_version | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
        echo -e "  ${GREEN}✓${NC} Python $python_version (>= 3.9 required)"
    else
        echo -e "  ${RED}✗${NC} Python $python_version (3.9+ required)"
        all_good=false
    fi
fi

# Check Node version
echo -e "\n${YELLOW}Checking Node.js version...${NC}"
node_version=$(node --version 2>&1 | grep -oE '[0-9]+')
if [ ! -z "$node_version" ] && [ "$node_version" -ge 18 ]; then
    echo -e "  ${GREEN}✓${NC} Node.js v$node_version (>= 18 required)"
else
    echo -e "  ${RED}✗${NC} Node.js version too old (18+ required)"
    all_good=false
fi

# Check disk space
echo -e "\n${YELLOW}Checking disk space...${NC}"
available_gb=$(df -BG . | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "$available_gb" -gt 10 ]; then
    echo -e "  ${GREEN}✓${NC} ${available_gb}GB available (>10GB recommended)"
else
    echo -e "  ${YELLOW}⚠${NC}  Only ${available_gb}GB available (>10GB recommended)"
fi

# Summary
echo -e "\n${BLUE}================================${NC}"
if [ "$all_good" = true ]; then
    echo -e "${GREEN}✓ System is ready for development!${NC}"
    echo -e "\nRun: ${BLUE}./dev.sh${NC} to start"
else
    echo -e "${RED}✗ Some requirements are missing${NC}"
    echo -e "\nPlease install missing dependencies and try again"
    exit 1
fi
echo -e "${BLUE}================================${NC}\n"
