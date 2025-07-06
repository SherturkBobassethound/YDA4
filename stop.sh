#!/bin/bash

# YODA Application Stop Script
# This script stops all YODA containers

echo "🛑 Stopping YODA Application..."
echo "================================"

# Stop all services
docker-compose down

echo "✅ All YODA services have been stopped."
echo ""
echo "ℹ️  To remove all data volumes as well, run:"
echo "   docker-compose down -v"
echo ""
echo "🗑️  To clean up completely (including images), run:"
echo "   docker-compose down --rmi all -v --remove-orphans"