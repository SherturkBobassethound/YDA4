#!/bin/bash

# Complete setup script with frontend options
set -e

echo "🚀 Setting up Complete Podcast Transcription App..."
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker."
    exit 1
fi

print_status "Docker is running"

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
elif docker compose version &> /dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
else
    print_error "Docker Compose is not available."
    exit 1
fi

print_status "Docker Compose is available"

# Ask user for setup type
echo ""
echo "Choose your setup:"
echo "1) Development (Frontend with hot reload on port 5173)"
echo "2) Production (Frontend with nginx on port 80)"
echo "3) Backend only (Use local frontend)"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        COMPOSE_FILE="docker-compose.dev.yml"
        FRONTEND_URL="http://localhost:5173"
        MODE="Development"
        ;;
    2)
        COMPOSE_FILE="docker-compose.yml"
        FRONTEND_URL="http://localhost"
        MODE="Production"
        ;;
    3)
        COMPOSE_FILE="docker-compose.backend-only.yml"
        FRONTEND_URL="http://localhost:5173 (run locally with 'deno task dev')"
        MODE="Backend Only"
        ;;
    *)
        print_error "Invalid choice. Using Production mode."
        COMPOSE_FILE="docker-compose.yml"
        FRONTEND_URL="http://localhost"
        MODE="Production"
        ;;
esac

print_info "Using $MODE mode with $COMPOSE_FILE"

# Create .env file if needed
if [ ! -f .env ]; then
    print_info "Creating .env file..."
    cat > .env << 'EOF'
OPENAI_API_KEY=your-openai-api-key-here
EOF
    print_warning "Please edit .env file and add your OpenAI API key!"
fi

# Create backend-only compose file if needed
if [ "$choice" = "3" ]; then
    print_info "Creating backend-only docker-compose file..."
    cat > docker-compose.backend-only.yml << 'EOF'
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  backend:
    build: 
      context: ./app/backend
      dockerfile: Dockerfile
    container_name: backend
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OLLAMA_BASE_URL=http://ollama:11434
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - ollama
      - qdrant
    volumes:
      - ./app/backend:/app
      - /tmp:/tmp
    restart: unless-stopped

volumes:
  ollama_data:
  qdrant_data:
EOF
fi

# Build and start services
echo ""
print_info "Building and starting services..."
$DOCKER_COMPOSE -f $COMPOSE_FILE up --build -d

# Wait for services
echo ""
print_info "Waiting for services to start..."

wait_for_service() {
    local service_name=$1
    local url=$2
    local max_attempts=60
    local attempt=1
    
    echo -n "Waiting for $service_name"
    while [ $attempt -le $max_attempts ]; do
        if curl -f "$url" > /dev/null 2>&1; then
            echo ""
            print_status "$service_name is healthy"
            return 0
        fi
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    echo ""
    print_error "$service_name failed to start"
    return 1
}

# Check services
wait_for_service "Qdrant" "http://localhost:6333/"
wait_for_service "Ollama" "http://localhost:11434/api/version"

# Pull Ollama model
print_info "Pulling Ollama model..."
$DOCKER_COMPOSE -f $COMPOSE_FILE exec ollama ollama pull llama3.2:3b
print_status "Ollama model downloaded"

wait_for_service "Backend" "http://localhost:8000/health"

if [ "$choice" != "3" ]; then
    if [ "$choice" = "1" ]; then
        wait_for_service "Frontend (Dev)" "http://localhost:5173"
    else
        wait_for_service "Frontend (Prod)" "http://localhost/health"
    fi
fi

# Final summary
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Your app is running in $MODE mode:"
echo "   Frontend:  $FRONTEND_URL"
echo "   Backend:   http://localhost:8000"
echo "   Ollama:    http://localhost:11434"
echo "   Qdrant:    http://localhost:6333"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:     $DOCKER_COMPOSE -f $COMPOSE_FILE logs -f [service]"
echo "   Stop all:      $DOCKER_COMPOSE -f $COMPOSE_FILE down"
echo "   Restart:       $DOCKER_COMPOSE -f $COMPOSE_FILE restart [service]"
echo "   Rebuild:       $DOCKER_COMPOSE -f $COMPOSE_FILE up --build"
echo ""

if [ "$choice" = "3" ]; then
    print_info "To start your local frontend:"
    echo "   cd app/frontend && deno task dev"
fi

print_info "Your podcast app is ready! 🚀"