#!/bin/bash

# YODA Fly.io Deployment Script
# This script deploys all three services to Fly.io: Ollama, Backend, and Frontend

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Check if fly CLI is installed
if ! command -v fly &> /dev/null; then
    print_error "Fly CLI is not installed. Please install it from https://fly.io/docs/getting-started/installing-flyctl/"
    exit 1
fi

print_status "Fly CLI found"

# Check if user is logged in
if ! fly auth whoami &> /dev/null; then
    print_error "Not logged in to Fly.io. Please run: fly auth login"
    exit 1
fi

print_status "Logged in to Fly.io as $(fly auth whoami)"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create one from .env.example"
    exit 1
fi

print_status ".env file found"

# Load environment variables from .env
export $(grep -v '^#' .env | xargs)

# Validate required environment variables
REQUIRED_VARS=("SUPABASE_URL" "SUPABASE_ANON_KEY" "SUPABASE_JWT_SECRET" "SUPABASE_SERVICE_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    print_error "Missing required environment variables: ${MISSING_VARS[*]}"
    exit 1
fi

print_status "All required environment variables found"

echo ""
echo "=========================================="
echo "  YODA Fly.io Deployment"
echo "=========================================="
echo ""

# Step 1: Deploy Ollama service
echo "Step 1: Deploying Ollama service..."
cd ollama-fly

# Check if app exists, if not create it
if ! fly apps list | grep -q "yoda-ollama"; then
    print_info "Creating yoda-ollama app..."
    fly apps create yoda-ollama --org personal || true
fi

# Deploy Ollama
print_info "Deploying Ollama service..."
fly deploy --app yoda-ollama

# Create volume if it doesn't exist
if ! fly volumes list --app yoda-ollama | grep -q "ollama_data"; then
    print_info "Creating ollama_data volume..."
    fly volumes create ollama_data --app yoda-ollama --region sjc --size 5
fi

print_status "Ollama service deployed"
cd ..

# Step 2: Deploy Backend service
echo ""
echo "Step 2: Deploying Backend service..."
cd app/backend

# Check if app exists, if not create it
if ! fly apps list | grep -q "yoda-backend"; then
    print_info "Creating yoda-backend app..."
    fly apps create yoda-backend --org personal || true
fi

# Set secrets for backend
print_info "Setting backend secrets..."
fly secrets set \
    SUPABASE_URL="$SUPABASE_URL" \
    SUPABASE_ANON_KEY="$SUPABASE_ANON_KEY" \
    SUPABASE_JWT_SECRET="$SUPABASE_JWT_SECRET" \
    SUPABASE_SERVICE_KEY="$SUPABASE_SERVICE_KEY" \
    OLLAMA_BASE_URL="http://yoda-ollama.internal:11434" \
    FRONTEND_URL="https://yoda-frontend.fly.dev" \
    ENVIRONMENT="production" \
    --app yoda-backend

# Create private network connection to Ollama
print_info "Creating private network connection to Ollama..."
fly proxy create --app yoda-backend --port 11434 --target yoda-ollama:11434 || true

# Deploy backend
print_info "Deploying backend service..."
fly deploy --app yoda-backend

print_status "Backend service deployed"
BACKEND_URL=$(fly status --app yoda-backend | grep "Hostname" | awk '{print $2}' || echo "yoda-backend.fly.dev")
print_info "Backend URL: https://$BACKEND_URL"
cd ../..

# Step 3: Deploy Frontend service
echo ""
echo "Step 3: Deploying Frontend service..."
cd app/frontend

# Check if app exists, if not create it
if ! fly apps list | grep -q "yoda-frontend"; then
    print_info "Creating yoda-frontend app..."
    fly apps create yoda-frontend --org personal || true
fi

# Deploy frontend
# Note: Fly.io doesn't support --build-arg directly
# We need to create a .env.production file or use build secrets
# For now, we'll create a temporary .env.production file during build
print_info "Creating .env.production file for build..."
cat > .env.production << EOF
VITE_API_BASE_URL=https://$BACKEND_URL
VITE_SUPABASE_URL=$SUPABASE_URL
VITE_SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY
EOF

# Deploy frontend
print_info "Deploying frontend service..."
fly deploy --app yoda-frontend

# Clean up .env.production (optional, as it's in .gitignore)
rm -f .env.production

print_status "Frontend service deployed"
FRONTEND_URL=$(fly status --app yoda-frontend | grep "Hostname" | awk '{print $2}' || echo "yoda-frontend.fly.dev")
print_info "Frontend URL: https://$FRONTEND_URL"
cd ../..

# Step 4: Update backend CORS with actual frontend URL
echo ""
echo "Step 4: Updating backend CORS configuration..."
cd app/backend
fly secrets set FRONTEND_URL="https://$FRONTEND_URL" --app yoda-backend
cd ../..

# Step 5: Pull initial Ollama model
echo ""
echo "Step 5: Setting up Ollama model..."
print_info "Pulling llama3.2:1b model (this may take a few minutes)..."
fly ssh console --app yoda-ollama -C "ollama pull llama3.2:1b" || print_warning "Could not pull model automatically. Please SSH into the Ollama instance and run: ollama pull llama3.2:1b"

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
print_status "Frontend: https://$FRONTEND_URL"
print_status "Backend: https://$BACKEND_URL"
print_status "Ollama: https://yoda-ollama.fly.dev"
echo ""
print_info "Next steps:"
echo "  1. Visit https://$FRONTEND_URL to access the application"
echo "  2. If Ollama model wasn't pulled, SSH in and run: fly ssh console --app yoda-ollama -C 'ollama pull llama3.2:1b'"
echo "  3. Check logs: fly logs --app yoda-backend"
echo ""

