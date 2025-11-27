# Makefile for YODA

.PHONY: help dev prod stop logs setup clean

# Default target
help:
	@echo "YODA Commands:"
	@echo ""
	@echo "  make dev          - Start local development (hot-reload)"
	@echo "  make prod         - Start Docker production (builds and runs)"
	@echo "  make stop         - Stop all services"
	@echo "  make logs         - Show all service logs"
	@echo "  make setup        - Run interactive setup wizard"
	@echo "  make clean        - Clean up dev environment and Docker volumes"
	@echo ""

# Start local development
dev:
	@./dev.sh

# Start Docker production
prod:
	@echo "🚀 Starting YODA in production mode..."
	@docker compose up --build -d
	@echo "✅ Services started! Visit http://localhost"

# Stop all services
stop:
	@echo "🛑 Stopping services..."
	@docker compose down
	@echo "✅ Services stopped"

# Show logs
logs:
	@docker compose logs -f

# Run setup wizard
setup:
	@./setup_supabase_env.sh

# Clean up environment
clean:
	@echo "🧹 Cleaning up..."
	@rm -rf venv
	@rm -rf app/frontend/node_modules
	@rm -rf logs
	@docker compose down -v
	@echo "✅ Cleaned"
