#!/bin/bash

# YODA Application Stop Script
# This script stops all YODA containers
#
# Usage:
#   ./stop.sh           - Stop containers (preserve data)
#   ./stop.sh --clean   - Stop and remove volumes (fresh start)
#   ./stop.sh --purge   - Stop, remove volumes and images (complete cleanup)

# Detect mode
CLEAN_MODE=false
PURGE_MODE=false

if [ "$1" = "--clean" ]; then
    CLEAN_MODE=true
    echo "🧹 Stopping YODA Application and removing data volumes..."
    echo "=========================================================="
elif [ "$1" = "--purge" ]; then
    PURGE_MODE=true
    echo "🗑️  Stopping YODA Application and purging everything..."
    echo "======================================================="
else
    echo "🛑 Stopping YODA Application..."
    echo "================================"
fi

# Stop services based on mode
if [ "$PURGE_MODE" = true ]; then
    docker-compose down --rmi all -v --remove-orphans
    echo "✅ All services stopped, images removed, and data purged."
elif [ "$CLEAN_MODE" = true ]; then
    docker-compose down -v --remove-orphans
    echo "✅ All services stopped and data volumes removed."
else
    docker-compose down --remove-orphans
    echo "✅ All YODA services have been stopped (data preserved)."
fi

echo ""
echo "📚 Available stop options:"
echo "   ./stop.sh         - Stop containers, keep data"
echo "   ./stop.sh --clean - Stop and remove data (fresh start)"
echo "   ./stop.sh --purge - Remove everything (images + data)"
echo ""
echo "🚀 To restart: ./start.sh --dev"