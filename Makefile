# Makefile for YODA Development

.PHONY: help dev stop clean install docker-dev docker-prod logs

# Default target
help:
	@echo "YODA Development Commands:"
	@echo ""
	@echo "  make dev          - Start local development (hot-reload)"
	@echo "  make stop         - Stop all development services"
	@echo "  make clean        - Clean up dev environment"
	@echo "  make install      - Install all dependencies"
	@echo "  make docker-dev   - Start Docker dev dependencies only"
	@echo "  make docker-prod  - Start full Docker production setup"
	@echo "  make logs         - Show all service logs"
	@echo ""

# Start local development
dev:
	@./dev.sh

# Stop all services
stop:
	@./dev-stop.sh

# Clean up development environment
clean:
	@echo "Cleaning development environment..."
	@rm -rf venv
	@rm -rf app/frontend/node_modules
	@rm -rf logs
	@docker-compose -f docker-compose.dev.yml down -v
	@echo "✓ Cleaned"

# Install all dependencies
install:
	@echo "Installing dependencies..."
	@python3 -m venv venv
	@. venv/bin/activate && cd app/backend && pip install -r requirements.txt
	@. venv/bin/activate && cd app/ollama-service && pip install -r requirements.txt
	@cd app/frontend && npm install
	@echo "✓ All dependencies installed"

# Start Docker dev dependencies only
docker-dev:
	@docker-compose -f docker-compose.dev.yml up -d
	@echo "✓ Docker services started (Qdrant & Ollama)"

# Start full Docker production setup
docker-prod:
	@docker-compose up -d
	@echo "✓ Production Docker services started"

# Show logs
logs:
	@echo "=== Backend Logs ==="
	@tail -20 logs/backend.log 2>/dev/null || echo "No backend logs"
	@echo ""
	@echo "=== Ollama API Logs ==="
	@tail -20 logs/ollama-api.log 2>/dev/null || echo "No ollama-api logs"
	@echo ""
	@echo "=== Frontend Logs ==="
	@tail -20 logs/frontend.log 2>/dev/null || echo "No frontend logs"
