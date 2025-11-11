#!/bin/bash

# YODA Application Startup Script - Robust Version
# This script handles health check issues and ensures all services start properly
#
# Usage:
#   ./start.sh           - Normal start with health checks
#   ./start.sh --dev     - Quick development mode (rebuilds code, minimal checks)
#   ./start.sh --rebuild - Full rebuild from scratch

set -e  # Exit on any error

# Detect mode
DEV_MODE=false
REBUILD_MODE=false

if [ "$1" = "--dev" ]; then
    DEV_MODE=true
    echo "🔧 Starting YODA Application in DEVELOPMENT MODE..."
    echo "   (Rebuilding services to pick up code changes)"
elif [ "$1" = "--rebuild" ]; then
    REBUILD_MODE=true
    echo "🔄 Starting YODA Application with FULL REBUILD..."
else
    echo "🚀 Starting YODA Application..."
fi
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ Error: docker-compose is not installed. Please install docker-compose and try again."
    exit 1
fi

# Find the docker-compose.yml file
if [ -f "docker-compose.yml" ]; then
    echo "📁 Found docker-compose.yml in current directory"
    COMPOSE_FILE="docker-compose.yml"
elif [ -f "../docker-compose.yml" ]; then
    echo "📁 Found docker-compose.yml in parent directory"
    COMPOSE_FILE="../docker-compose.yml"
else
    echo "❌ Error: Could not find docker-compose.yml file"
    echo "   Make sure you're running this script from the correct directory"
    exit 1
fi

# Check for environment file and create if needed
if [ ! -f ".env" ]; then
    echo "📋 No .env file found. Creating from template..."
    if [ -f ".env.production" ]; then
        cp .env.production .env
        echo "✅ Created .env file from production template"
    elif [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file from example template"
    else
        echo "⚠️  No environment template found. Using default configuration."
    fi
fi

# Function to check if a service is responding (without relying on health checks)
check_service_response() {
    local service_name=$1
    local url=$2
    local max_attempts=60
    local attempt=1
    
    echo "⏳ Checking $service_name response..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s -m 5 "$url" > /dev/null 2>&1; then
            echo "✅ $service_name is responding!"
            return 0
        fi
        
        if [ $((attempt % 10)) -eq 0 ]; then
            echo "   Attempt $attempt/$max_attempts - waiting for $service_name..."
        fi
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo "⚠️  $service_name not responding, but continuing..."
    return 1
}

# Function to check Qdrant specifically (it has different endpoints)
check_qdrant_health() {
    local max_attempts=60
    local attempt=1
    
    echo "⏳ Checking Qdrant health..."
    
    while [ $attempt -le $max_attempts ]; do
        # Try multiple Qdrant endpoints
        if curl -f -s -m 5 "http://localhost:6333/collections" > /dev/null 2>&1; then
            echo "✅ Qdrant is healthy (collections endpoint responding)!"
            return 0
        elif curl -f -s -m 5 "http://localhost:6333/" > /dev/null 2>&1; then
            echo "✅ Qdrant is healthy (root endpoint responding)!"
            return 0
        fi
        
        if [ $((attempt % 10)) -eq 0 ]; then
            echo "   Attempt $attempt/$max_attempts - waiting for Qdrant..."
        fi
        sleep 3
        attempt=$((attempt + 1))
    done
    
    echo "⚠️  Qdrant not responding, but continuing..."
    return 1
}

# Function to check container status
check_container_running() {
    local container_name=$1
    if docker ps --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        echo "✅ $container_name is running"
        return 0
    else
        echo "❌ $container_name is not running"
        return 1
    fi
}

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose -f "$COMPOSE_FILE" down --remove-orphans > /dev/null 2>&1 || true

# Clean up any orphaned containers or networks
echo "🧹 Cleaning up orphaned resources..."
docker system prune -f > /dev/null 2>&1 || true

# Build images based on mode
if [ "$REBUILD_MODE" = true ]; then
    echo "🔄 Rebuilding all images from scratch..."
    docker-compose -f "$COMPOSE_FILE" build --no-cache
elif [ "$DEV_MODE" = true ]; then
    echo "🏗️  Rebuilding code services (backend, frontend, ollama-api)..."
    docker-compose -f "$COMPOSE_FILE" build backend frontend ollama-api
else
    echo "🏗️  Building images (if needed)..."
    docker-compose -f "$COMPOSE_FILE" build
fi

# Create a simplified compose override to bypass health check dependencies
echo "🔧 Creating temporary override to handle health check issues..."
cat > docker-compose.override.yml << 'EOF'
services:
  ollama-api:
    depends_on:
      - ollama
    # Remove health check dependency

  backend:
    depends_on:
      - qdrant
      - ollama-api
    # Remove health check dependency

  frontend:
    depends_on:
      - backend
    # Remove health check dependency
EOF

# Start services based on mode
if [ "$DEV_MODE" = true ]; then
    echo "🚀 Starting all services (quick mode)..."
    docker-compose -f "$COMPOSE_FILE" up -d
    echo "⏳ Waiting 30 seconds for services to initialize..."
    sleep 30
else
    # Start services in stages to avoid dependency issues
    echo "🚀 Starting core services..."

    # Stage 1: Start base services (Qdrant and Ollama)
    echo "📊 Starting Qdrant (Vector Database)..."
    docker-compose -f "$COMPOSE_FILE" up -d qdrant
    sleep 10

    echo "🤖 Starting Ollama (LLM Service)..."
    docker-compose -f "$COMPOSE_FILE" up -d ollama
    sleep 15

    # Stage 2: Check core services
    echo ""
    echo "🔍 Checking core services..."
    check_qdrant_health
    check_service_response "Ollama" "http://localhost:11434/api/version"

    # Stage 3: Start API services (force start without health check dependencies)
    echo ""
    echo "🔌 Starting API services..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps ollama-api
    sleep 15

    check_service_response "Ollama API" "http://localhost:8001/"

    # Stage 4: Start backend (force start without health check dependencies)
    echo ""
    echo "⚙️  Starting Backend API..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps backend
    sleep 20

    check_service_response "Backend API" "http://localhost:8000/health"

    # Stage 5: Start frontend (force start without health check dependencies)
    echo ""
    echo "🌐 Starting Frontend..."
    docker-compose -f "$COMPOSE_FILE" up -d --no-deps frontend
    sleep 10

    check_service_response "Frontend" "http://localhost/health"
fi

# Clean up temporary override
rm -f docker-compose.override.yml

echo ""
echo "🎉 YODA Application Started!"
echo "=================================="
echo ""

# Show final status
echo "📊 Container Status:"
docker-compose -f "$COMPOSE_FILE" ps

echo ""
echo "📱 Application URLs:"
echo "   Frontend:    http://localhost"
echo "   Backend API: http://localhost:8000"
echo "   Ollama API:  http://localhost:8001"
echo "   Qdrant DB:   http://localhost:6333"
echo "   Ollama:      http://localhost:11434"
echo ""

# Final health check
echo "📋 Service Health Check:"
services_working=0

echo -n "   Qdrant:      "
if curl -f -s -m 5 "http://localhost:6333/collections" > /dev/null 2>&1; then
    echo "✅ Online"
    ((services_working++))
elif curl -f -s -m 5 "http://localhost:6333/" > /dev/null 2>&1; then
    echo "✅ Online (basic)"
    ((services_working++))
else
    echo "❌ Offline"
fi

echo -n "   Ollama:      "
if curl -f -s -m 5 "http://localhost:11434/api/version" > /dev/null 2>&1; then
    echo "✅ Online"
    ((services_working++))
else
    echo "❌ Offline"
fi

echo -n "   Ollama API:  "
if curl -f -s -m 5 "http://localhost:8001/" > /dev/null 2>&1; then
    echo "✅ Online"
    ((services_working++))
else
    echo "❌ Offline"
fi

echo -n "   Backend API: "
if curl -f -s -m 5 "http://localhost:8000/health" > /dev/null 2>&1; then
    echo "✅ Online"
    ((services_working++))
else
    echo "❌ Offline"
fi

echo -n "   Frontend:    "
if curl -f -s -m 5 "http://localhost/health" > /dev/null 2>&1; then
    echo "✅ Online"
    ((services_working++))
else
    echo "❌ Offline"
fi

echo ""
echo "📈 Services Status: $services_working/5 services responding"

if [ $services_working -ge 3 ]; then
    echo "🎯 YODA is ready! Open http://localhost to start using the app"
else
    echo "⚠️  Some services may still be starting. Wait a minute and try http://localhost"
    echo "   If issues persist, check logs with: docker-compose logs [service_name]"
fi

if [ "$DEV_MODE" = false ]; then
    echo ""
    echo "🤖 Ollama Models:"
    if docker exec ollama_service ollama list 2>/dev/null | grep -q "NAME"; then
        docker exec ollama_service ollama list 2>/dev/null
    else
        echo "   No models installed yet"
        echo ""
        read -p "🤖 Would you like to install the default models now? (y/N): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "📥 Installing llama3.2:1b (lightweight model)..."
            if docker exec ollama_service ollama pull llama3.2:1b 2>/dev/null; then
                echo "✅ llama3.2:1b installed successfully!"
            else
                echo "❌ Failed to install llama3.2:1b"
            fi

            echo "📥 Installing llama3.2:3b (more capable model)..."
            if docker exec ollama_service ollama pull llama3.2:3b 2>/dev/null; then
                echo "✅ llama3.2:3b installed successfully!"
            else
                echo "❌ Failed to install llama3.2:3b"
            fi
        fi
    fi
fi

echo ""
echo "📚 Useful Commands:"
echo "   View all logs:      docker-compose logs -f"
echo "   View service log:   docker-compose logs -f [service_name]"
echo "   Stop all:           ./stop.sh"
echo "   Restart service:    docker-compose restart [service_name]"
echo "   Quick deploy:       ./stop.sh && ./start.sh --dev"
echo "   Full rebuild:       ./start.sh --rebuild"
echo ""

# Show resource usage
echo "💻 Resource Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null || echo "   Could not retrieve resource stats"

echo ""
echo "🎉 Setup complete! Happy transcribing! 🎙️✨"