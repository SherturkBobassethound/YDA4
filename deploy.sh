#!/bin/bash

# YODA Quick Deploy Script
# This script stops, rebuilds, and restarts your application with code changes
#
# Usage:
#   ./deploy.sh         - Quick deploy with code rebuild
#   ./deploy.sh --clean - Deploy with fresh data (removes volumes)

set -e  # Exit on any error

echo "🚢 YODA Quick Deploy"
echo "===================="
echo ""

# Check for clean flag
CLEAN_FLAG=""
if [ "$1" = "--clean" ]; then
    CLEAN_FLAG="--clean"
    echo "📋 Mode: Clean deploy (removing data volumes)"
else
    echo "📋 Mode: Quick deploy (preserving data)"
fi

echo ""

# Stop existing services
if [ -n "$CLEAN_FLAG" ]; then
    ./stop.sh --clean
else
    ./stop.sh
fi

echo ""
echo "⏳ Waiting 3 seconds before restart..."
sleep 3
echo ""

# Start services in dev mode
./start.sh --dev

echo ""
echo "✨ Deploy complete!"
echo ""
echo "💡 Tip: Your code changes are now running in Docker"
echo "   Make edits, then run './deploy.sh' again to update"
