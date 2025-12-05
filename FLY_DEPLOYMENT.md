# Fly.io Deployment Guide for YODA

This guide will help you deploy the YODA application to Fly.io. The application consists of three services:
1. **Ollama** - LLM service for chat and summarization
2. **Backend** - FastAPI application with Whisper transcription
3. **Frontend** - Vue.js application served via nginx

## Prerequisites

1. **Fly.io Account**: Sign up at [fly.io](https://fly.io) if you don't have one
2. **Fly CLI**: Install the Fly CLI:
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```
   Or follow the [official installation guide](https://fly.io/docs/getting-started/installing-flyctl/)

3. **Login to Fly.io**:
   ```bash
   fly auth login
   ```

4. **Supabase Setup**: Ensure you have:
   - A Supabase project created
   - All migrations run (see README.md)
   - Your `.env` file configured with Supabase credentials

## Quick Deployment (Automated)

The easiest way to deploy is using the provided deployment script:

```bash
./deploy-fly.sh
```

This script will:
- Deploy all three services in the correct order
- Set up private networking between services
- Configure all necessary secrets
- Pull the initial Ollama model

## Manual Deployment

If you prefer to deploy manually or need more control, follow these steps:

### Step 1: Deploy Ollama Service

```bash
cd ollama-fly

# Create the app (if it doesn't exist)
fly apps create yoda-ollama --org personal

# Create volume for Ollama data (5GB)
fly volumes create ollama_data --app yoda-ollama --region sjc --size 5

# Deploy
fly deploy --app yoda-ollama

# Pull the default model (this may take a few minutes)
fly ssh console --app yoda-ollama -C "ollama pull llama3.2:1b"

cd ..
```

### Step 2: Deploy Backend Service

```bash
cd app/backend

# Create the app (if it doesn't exist)
fly apps create yoda-backend --org personal

# Set secrets (replace with your actual values from .env)
fly secrets set \
    SUPABASE_URL="https://your-project.supabase.co" \
    SUPABASE_ANON_KEY="your-anon-key" \
    SUPABASE_JWT_SECRET="your-jwt-secret" \
    SUPABASE_SERVICE_KEY="your-service-key" \
    OLLAMA_BASE_URL="http://yoda-ollama.internal:11434" \
    FRONTEND_URL="https://yoda-frontend.fly.dev" \
    ENVIRONMENT="production" \
    --app yoda-backend

# Create private network connection to Ollama
fly proxy create --app yoda-backend --port 11434 --target yoda-ollama:11434

# Deploy
fly deploy --app yoda-backend

# Get the backend URL
fly status --app yoda-backend

cd ../..
```

**Note**: The `OLLAMA_BASE_URL` uses Fly.io's private networking (`*.internal` domain) to connect to the Ollama service without exposing it publicly.

### Step 3: Deploy Frontend Service

```bash
cd app/frontend

# Create the app (if it doesn't exist)
fly apps create yoda-frontend --org personal

# Get backend URL (from previous step)
BACKEND_URL="yoda-backend.fly.dev"  # Replace with actual URL

# Create .env.production file for Vite build
# Vite automatically reads .env.production during build
cat > .env.production << EOF
VITE_API_BASE_URL=https://$BACKEND_URL
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key
EOF

# Deploy (Vite will use .env.production during build)
fly deploy --app yoda-frontend

# Clean up (optional, .env.production should be in .gitignore)
rm -f .env.production

# Get the frontend URL
fly status --app yoda-frontend

cd ../..
```

### Step 4: Update Backend CORS

After deploying the frontend, update the backend's CORS configuration with the actual frontend URL:

```bash
cd app/backend
fly secrets set FRONTEND_URL="https://yoda-frontend.fly.dev" --app yoda-backend
cd ../..
```

## Service URLs

After deployment, you'll have:

- **Frontend**: `https://yoda-frontend.fly.dev`
- **Backend**: `https://yoda-backend.fly.dev`
- **Ollama**: `https://yoda-ollama.fly.dev` (internal only, not publicly accessible)

## Private Networking

The backend connects to Ollama using Fly.io's private networking:
- Backend → Ollama: `http://yoda-ollama.internal:11434`
- This keeps Ollama private and doesn't expose it to the internet

## Managing Secrets

To update secrets:

```bash
# Backend secrets
fly secrets set KEY="value" --app yoda-backend

# Frontend secrets (requires redeploy to take effect)
fly secrets set KEY="value" --app yoda-frontend
fly deploy --app yoda-frontend
```

To view secrets (values are hidden):
```bash
fly secrets list --app yoda-backend
```

## Viewing Logs

```bash
# Backend logs
fly logs --app yoda-backend

# Frontend logs
fly logs --app yoda-frontend

# Ollama logs
fly logs --app yoda-ollama

# Follow logs in real-time
fly logs --app yoda-backend --follow
```

## Scaling

### Backend
The backend is configured to always run (min_machines_running = 1) for better performance.

### Frontend
The frontend auto-stops when idle and auto-starts on traffic (cost-effective).

### Ollama
Ollama auto-stops when idle. First request after idle may take a moment to start.

## Troubleshooting

### Backend can't connect to Ollama

1. Check private networking:
   ```bash
   fly proxy list --app yoda-backend
   ```

2. Verify Ollama is running:
   ```bash
   fly status --app yoda-ollama
   ```

3. Check backend logs:
   ```bash
   fly logs --app yoda-backend
   ```

### Frontend can't connect to Backend

1. Verify backend URL in frontend secrets:
   ```bash
   fly secrets list --app yoda-frontend
   ```

2. Check CORS configuration in backend:
   ```bash
   fly secrets list --app yoda-backend | grep FRONTEND_URL
   ```

3. Test backend health:
   ```bash
   curl https://yoda-backend.fly.dev/health
   ```

### Ollama model not found

SSH into the Ollama instance and pull the model:
```bash
fly ssh console --app yoda-ollama
ollama pull llama3.2:1b
```

### Build failures

1. Check build logs:
   ```bash
   fly logs --app yoda-frontend
   ```

2. Verify build secrets are set:
   ```bash
   fly secrets list --app yoda-frontend
   ```

3. Try rebuilding:
   ```bash
   fly deploy --app yoda-frontend --no-cache
   ```

## Cost Optimization

- **Frontend**: Auto-stops when idle (free tier friendly)
- **Backend**: Always running (1GB RAM, ~$5-10/month)
- **Ollama**: Auto-stops when idle, but uses performance-1x VM (~$20-30/month when running)

To reduce costs:
- Use smaller VM sizes (adjust in `fly.toml`)
- Enable auto-stop for backend (change `min_machines_running = 0`)
- Use shared CPU instead of performance CPU for Ollama

## Updating the Application

To update after making changes:

```bash
# Update backend
cd app/backend
fly deploy --app yoda-backend
cd ../..

# Update frontend
cd app/frontend
fly deploy --app yoda-frontend
cd ../..

# Update Ollama (rarely needed)
cd ollama-fly
fly deploy --app yoda-ollama
cd ..
```

## Monitoring

Fly.io provides built-in monitoring:
- Visit your Fly.io dashboard: https://fly.io/dashboard
- View metrics, logs, and status for each app

## Support

For issues:
1. Check logs: `fly logs --app <app-name>`
2. Check status: `fly status --app <app-name>`
3. Visit Fly.io docs: https://fly.io/docs

