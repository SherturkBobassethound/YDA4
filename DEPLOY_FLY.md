# Deploying YODA to Fly.io

This guide walks you through deploying YODA (Your Own Data Assistant) to Fly.io.

## Prerequisites

1. **Fly.io CLI**: Install the Fly.io CLI
   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. **Fly.io Account**: Sign up or log in
   ```bash
   fly auth login
   ```

3. **Supabase Project**: You need your Supabase credentials from your existing project:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_JWT_SECRET`
   - `SUPABASE_SERVICE_KEY`

## Deployment Steps

### 1. Deploy Backend

Navigate to the backend directory and launch the app:

```bash
cd app/backend
fly launch --no-deploy
```

When prompted:
- Choose a unique app name (or accept the suggested one)
- Select a region (e.g., `iad` for US East)
- Say "No" to PostgreSQL database
- Say "No" to Redis

Set your environment secrets:

```bash
fly secrets set \
  SUPABASE_URL="your-supabase-url" \
  SUPABASE_ANON_KEY="your-supabase-anon-key" \
  SUPABASE_JWT_SECRET="your-supabase-jwt-secret" \
  SUPABASE_SERVICE_KEY="your-service-key" \
  OLLAMA_BASE_URL="http://your-ollama-instance:11434"
```

Deploy the backend:

```bash
fly deploy
```

Get your backend URL:

```bash
fly status
```

Note the hostname (e.g., `yoda-backend.fly.dev`).

### 2. Deploy Frontend

Navigate to the frontend directory and launch the app:

```bash
cd ../frontend
fly launch --no-deploy
```

When prompted:
- Choose a unique app name (or accept the suggested one)
- Select the same region as your backend
- Say "No" to PostgreSQL database
- Say "No" to Redis

Set your build arguments and secrets:

```bash
# Set build-time environment variables
fly secrets set \
  VITE_SUPABASE_URL="your-supabase-url" \
  VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" \
  VITE_API_BASE_URL="https://yoda-backend.fly.dev"
```

Deploy the frontend:

```bash
fly deploy \
  --build-arg VITE_SUPABASE_URL="your-supabase-url" \
  --build-arg VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" \
  --build-arg VITE_API_BASE_URL="https://yoda-backend.fly.dev"
```

### 3. Verify Deployment

Check backend health:
```bash
curl https://yoda-backend.fly.dev/health
```

Check frontend health:
```bash
curl https://yoda-frontend.fly.dev/health
```

Visit your app:
```
https://yoda-frontend.fly.dev
```

## Configuration Notes

### App Names
The default app names in `fly.toml` are:
- Backend: `yoda-backend`
- Frontend: `yoda-frontend`

Update the `app` field in each `fly.toml` file if you want different names.

### Region
The default region is `iad` (US East). Change `primary_region` in `fly.toml` to use a different region. See available regions:
```bash
fly platform regions
```

### Scaling
Both apps are configured with auto-stop/start:
- Machines automatically stop when idle
- They start when a request comes in
- `min_machines_running = 0` to minimize costs

To keep machines always running:
```bash
fly scale count 1 --app yoda-backend
```

### Resources
Current allocation:
- Backend: 1GB RAM, 1 shared CPU
- Frontend: 512MB RAM, 1 shared CPU

To increase resources:
```bash
fly scale memory 2048 --app yoda-backend
```

## Ollama Configuration

The backend requires an Ollama instance. Options:

### Option 1: External Ollama Server
Point `OLLAMA_BASE_URL` to your own Ollama server:
```bash
fly secrets set OLLAMA_BASE_URL="http://your-ollama-server:11434" --app yoda-backend
```

### Option 2: Deploy Ollama on Fly.io
Create a new app for Ollama (requires performance machines):
```bash
fly launch --image ollama/ollama:latest --app yoda-ollama --vm-memory 8192
fly secrets set OLLAMA_HOST="0.0.0.0" --app yoda-ollama
```

Then update backend:
```bash
fly secrets set OLLAMA_BASE_URL="http://yoda-ollama.internal:11434" --app yoda-backend
```

### Option 3: Use Cloud LLM APIs
Modify the backend code to use OpenAI, Anthropic, or other cloud LLM providers instead of Ollama.

## Monitoring

View logs:
```bash
fly logs --app yoda-backend
fly logs --app yoda-frontend
```

Check app status:
```bash
fly status --app yoda-backend
fly status --app yoda-frontend
```

View metrics:
```bash
fly dashboard --app yoda-backend
```

## Troubleshooting

### Build Failures
If the build fails, check:
- Dockerfile paths are correct
- All required files are present
- No syntax errors in fly.toml

### Health Check Failures
- Backend: Verify `/health` endpoint is accessible
- Frontend: Verify nginx is serving the `/health` endpoint
- Check logs: `fly logs --app <app-name>`

### CORS Issues
If you get CORS errors:
1. Verify `VITE_API_BASE_URL` in frontend matches your backend URL
2. Check backend CORS configuration allows the frontend domain

### Environment Variables
To update environment variables:
```bash
fly secrets set KEY="value" --app <app-name>
```

To list secrets:
```bash
fly secrets list --app <app-name>
```

## Cost Optimization

- Auto-stop/start is enabled by default
- Machines stop after 5 minutes of inactivity
- No charges when machines are stopped
- Consider using `fly-replay` header for multi-region deployments

## Updating Your App

To deploy updates:

```bash
cd app/backend
fly deploy

cd ../frontend
fly deploy
```

## Clean Up

To remove apps:
```bash
fly apps destroy yoda-backend
fly apps destroy yoda-frontend
```
