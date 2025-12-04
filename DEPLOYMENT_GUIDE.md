# Complete YODA Deployment Guide for Fly.io

This comprehensive guide covers everything you need to deploy YODA (Your Own Data Assistant) to Fly.io.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Overview](#deployment-overview)
3. [Deploy Ollama](#deploy-ollama)
4. [Deploy Backend](#deploy-backend)
5. [Deploy Frontend](#deploy-frontend)
6. [Configuration Check](#configuration-check)
7. [Keep Machines Running](#keep-machines-running)
8. [Troubleshooting](#troubleshooting)
9. [Monitoring & Maintenance](#monitoring--maintenance)

---

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

---

## Deployment Overview

YODA consists of three main components:
1. **Ollama** - Private LLM service (runs on Fly.io)
2. **Backend** - FastAPI service (connects to Ollama and Supabase)
3. **Frontend** - Vue.js SPA (served via nginx)

**Deployment Order**: Ollama → Backend → Frontend

---

## Deploy Ollama

### Step 1: Create Volume and Deploy

```bash
cd ollama-fly

# Create the volume for model storage (same region as your backend)
fly volumes create ollama_data --region sjc --size 20

# Launch the app (don't deploy yet)
fly launch --no-deploy

# When prompted, use "yoda-ollama" as the app name and select region "sjc"

# Deploy Ollama
fly deploy
```

### Step 2: Pull Your LLM Model

SSH into your Ollama machine to download the model:

```bash
# Connect to the Ollama machine
fly ssh console --app yoda-ollama

# Inside the machine, pull your desired model
ollama pull MODEL_NAME

# Verify the model is ready
ollama list

# Exit the SSH session
exit
```

**Alternative**: Pull model via API (from your local machine):
```bash
# Get your Ollama app's public URL
OLLAMA_URL=$(fly status --app yoda-ollama | grep "Hostname" | awk '{print $2}')

# Pull the model via API
curl -X POST http://${OLLAMA_URL}:11434/api/pull -d '{"name": "MODEL_NAME"}'
```

### Model Options

Choose based on your needs:
- **phi** (2.7GB) - Fast, good for testing, lower quality
- **llama2** (3.8GB) - Balanced performance and quality
- **mistral** (4.1GB) - Better quality, slightly slower
- **codellama** (3.8GB) - Optimized for code tasks

Check available models at https://ollama.com/library

### Internal URL

Your backend will use: `http://yoda-ollama.internal:11434`

This URL is **only accessible from your other Fly.io apps**, not from the public internet. Maximum privacy!

### Verify Ollama is Running

```bash
# Check app status
fly status --app yoda-ollama

# View logs
fly logs --app yoda-ollama
```

---

## Deploy Backend

### Step 1: Set Backend Secrets

Navigate to the backend directory and set all required secrets:

```bash
cd app/backend

# Set all backend secrets at once
fly secrets set \
  SUPABASE_URL="your-supabase-url" \
  SUPABASE_ANON_KEY="your-supabase-anon-key" \
  SUPABASE_JWT_SECRET="your-supabase-jwt-secret" \
  SUPABASE_SERVICE_KEY="your-supabase-service-key" \
  OLLAMA_BASE_URL="http://yoda-ollama.internal:11434" \
  FRONTEND_URL="https://yoda-frontend.fly.dev" \
  --app yoda-backend
```

**Important**: Replace the Supabase values with your actual credentials.

### Step 2: Deploy Backend

```bash
fly deploy --app yoda-backend
```

### Step 3: Verify Backend Health

```bash
# Check backend status
fly status --app yoda-backend

# Test health endpoint
curl https://yoda-backend.fly.dev/health

# Check logs
fly logs --app yoda-backend
```

The health endpoint should show:
```json
{
  "status": "healthy",
  "whisper": "loaded",
  "ollama": "connected",
  "supabase": "connected"
}
```

**✅ Checkpoint:** Note your backend URL (e.g., `yoda-backend.fly.dev`)

---

## Deploy Frontend

### Step 1: Get Backend URL

```bash
# Get your backend URL
BACKEND_URL=$(fly status --app yoda-backend | grep "Hostname" | awk '{print "https://"$2}')
echo $BACKEND_URL
# Should output something like: https://yoda-backend.fly.dev
```

### Step 2: Deploy Frontend with Build Args

```bash
cd ../frontend

# Deploy with build arguments
fly deploy \
  --build-arg VITE_API_BASE_URL="https://yoda-backend.fly.dev" \
  --build-arg VITE_SUPABASE_URL="your-supabase-url" \
  --build-arg VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" \
  --app yoda-frontend
```

**Important**: Replace Supabase values with your actual credentials.

### Step 3: Verify Frontend

```bash
# Check frontend status
fly status --app yoda-frontend

# Test health endpoint
curl https://yoda-frontend.fly.dev/health

# Visit in browser
open https://yoda-frontend.fly.dev
```

**✅ Checkpoint:** Your app is now live!

---

## Configuration Check

### Issues Found and Fixed

#### 1. Backend CORS Configuration ✅ FIXED
**Issue**: Backend only allowed localhost origins in production, which would block requests from the Fly.io frontend domain.

**Fix**: 
- Added support for `FRONTEND_URL` environment variable
- Backend now accepts requests from the configured frontend domain
- Added comment in `fly.toml` with instructions to set the secret

**Action Required**:
```bash
fly secrets set FRONTEND_URL="https://yoda-frontend.fly.dev" --app yoda-backend
```

#### 2. Frontend API URL Fallback ✅ FIXED
**Issue**: Frontend fallback logic tried to append `:8000` to the current hostname, which wouldn't work in Fly.io production where backend is on a different domain.

**Fix**: 
- Improved fallback logic to detect Fly.io domains
- Added warning when `VITE_API_BASE_URL` is not set in production
- Frontend now properly requires the build-time environment variable

**Action Required**: Ensure `VITE_API_BASE_URL` is set during frontend deployment (see Frontend deployment section above).

#### 3. Frontend Build Args Documentation ✅ FIXED
**Issue**: `fly.toml` didn't document how to pass build arguments.

**Fix**: Added comments in `fly.toml` with deployment command examples.

### Verified Configurations

#### Backend (`app/backend/`)
- ✅ **Dockerfile**: Properly configured with Python 3.11, dependencies, and uvicorn
- ✅ **fly.toml**: 
  - Port 8000 correctly configured
  - Health check endpoint `/health` configured
  - Auto-stop/start enabled (can be disabled - see Keep Machines Running section)
  - Memory: 1GB
- ✅ **Health Endpoint**: `/health` exists and checks Ollama + Supabase connections
- ✅ **CORS**: Now properly configured for production

#### Frontend (`app/frontend/`)
- ✅ **Dockerfile**: Multi-stage build with Node.js build and nginx production
- ✅ **fly.toml**: 
  - Port 80 correctly configured
  - Health check endpoint `/health` configured
  - Auto-stop/start enabled (can be disabled - see Keep Machines Running section)
  - Memory: 512MB
- ✅ **nginx.conf**: 
  - Health endpoint at `/health` returns 200 OK
  - SPA routing configured (fallback to index.html)
  - Static asset caching configured
- ✅ **Health Check**: Dockerfile includes health check script

### Notes and Recommendations

#### Region Mismatch
- Backend region: `sjc` (San Jose)
- Frontend region: `iad` (Washington D.C.)
- **Recommendation**: Consider deploying both to the same region for lower latency. Update `primary_region` in `fly.toml` files if needed.

#### Environment Variables Required

**Backend Secrets** (set with `fly secrets set`):
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_JWT_SECRET`
- `SUPABASE_SERVICE_KEY`
- `OLLAMA_BASE_URL` (e.g., `http://yoda-ollama.internal:11434`)
- `FRONTEND_URL` (required for CORS)

**Frontend Build Args** (passed during `fly deploy`):
- `VITE_API_BASE_URL` (e.g., `https://yoda-backend.fly.dev`)
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

#### Memory Considerations
- Backend: 1GB may be tight for Whisper model loading. Consider monitoring and potentially increasing to 2GB if needed.
- Frontend: 512MB is sufficient for nginx serving static files.

#### Health Checks
Both apps have health checks configured:
- Backend: `GET /health` (30s interval, 10s timeout, 1m grace period)
- Frontend: `GET /health` (30s interval, 10s timeout, 30s grace period)

---

## Keep Machines Running

By default, Fly.io machines auto-stop when idle to save costs. To keep machines running 24/7:

### Configuration Applied

All three `fly.toml` files have been updated to prevent machines from auto-stopping:
- `auto_stop_machines = false`
- `min_machines_running = 1`

### Apply Changes

You have two options:

#### Option 1: Redeploy (Recommended)
Redeploy each app to apply the new configuration:

```bash
# Ollama
cd ollama-fly
fly deploy --app yoda-ollama

# Backend
cd ../app/backend
fly deploy --app yoda-backend

# Frontend
cd ../frontend
fly deploy --app yoda-frontend
```

#### Option 2: Use fly scale count (Faster)
Set minimum running machines without full redeploy:

```bash
# Keep at least 1 machine running for each app
fly scale count 1 --app yoda-ollama
fly scale count 1 --app yoda-backend
fly scale count 1 --app yoda-frontend
```

### Verify

Check that machines are running:

```bash
fly status --app yoda-ollama
fly status --app yoda-backend
fly status --app yoda-frontend
```

All should show `STATE = started` (not `stopped`).

### Cost Implications

⚠️ **Important**: Keeping machines running 24/7 will incur charges even when idle:
- **Ollama**: Performance-1x machine (~$0.02/hour)
- **Backend**: 1GB shared CPU (~$0.0004/hour)
- **Frontend**: 512MB shared CPU (~$0.0002/hour)

**Estimated monthly cost**: ~$15-20/month for all three apps running continuously.

### Revert to Auto-Stop (If Needed)

If you want to save costs and allow auto-stopping:

```bash
# Update fly.toml files back to:
# auto_stop_machines = 'stop'
# min_machines_running = 0

# Then set scale count to 0
fly scale count 0 --app yoda-ollama
fly scale count 0 --app yoda-backend
fly scale count 0 --app yoda-frontend
```

---

## Troubleshooting

### Backend can't connect to Ollama

If the backend health check shows `"ollama": "disconnected"`:

1. **Verify Ollama is running**:
   ```bash
   fly status --app yoda-ollama
   fly logs --app yoda-ollama
   ```

2. **Check internal networking**:
   ```bash
   # SSH into backend and test connection
   fly ssh console --app yoda-backend
   curl http://yoda-ollama.internal:11434/api/version
   ```

3. **Verify secret is set correctly**:
   ```bash
   fly secrets list --app yoda-backend
   # Should show OLLAMA_BASE_URL=http://yoda-ollama.internal:11434
   ```

### Frontend can't connect to Backend

1. **Check CORS**: Ensure `FRONTEND_URL` secret is set correctly
2. **Verify API URL**: Check browser console for CORS errors
3. **Test backend directly**: `curl https://yoda-backend.fly.dev/health`

### Models not available

If you get errors about missing models:

```bash
# SSH into Ollama machine
fly ssh console --app yoda-ollama

# Pull your chosen model (replace MODEL_NAME with your model)
ollama pull MODEL_NAME

# List available models
ollama list
```

**Note**: Make sure the model name matches what your backend/frontend is configured to use.

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
3. Ensure `FRONTEND_URL` secret is set in backend

### Environment Variables

To update environment variables:
```bash
fly secrets set KEY="value" --app <app-name>
```

To list secrets:
```bash
fly secrets list --app <app-name>
```

### Ollama model not responding

```bash
# Check Ollama logs
fly logs --app yoda-ollama

# Restart Ollama
fly machine restart --app yoda-ollama

# SSH in and verify model
fly ssh console --app yoda-ollama
ollama list
```

---

## Monitoring & Maintenance

### View Logs

```bash
# View real-time logs
fly logs --app yoda-ollama
fly logs --app yoda-backend
fly logs --app yoda-frontend
```

### Check Status

```bash
# Check all app statuses
fly status --app yoda-ollama
fly status --app yoda-backend
fly status --app yoda-frontend
```

### Open Dashboard

```bash
fly dashboard --app yoda-backend
```

### Quick Reference Commands

```bash
# Check all app statuses
fly status --app yoda-ollama
fly status --app yoda-backend
fly status --app yoda-frontend

# View logs
fly logs --app yoda-ollama
fly logs --app yoda-backend
fly logs --app yoda-frontend

# SSH into machines
fly ssh console --app yoda-ollama
fly ssh console --app yoda-backend

# Update secrets
fly secrets set KEY="value" --app yoda-backend

# Redeploy
fly deploy --app yoda-backend
fly deploy --app yoda-frontend
```

### Updating Your Deployment

When you make code changes:

```bash
# Update backend
cd app/backend
fly deploy

# Update frontend
cd ../frontend
fly deploy
```

### Scaling Resources

To increase resources:

```bash
# Increase backend memory
fly scale memory 2048 --app yoda-backend

# Increase CPU
fly scale vm shared-cpu-2x --app yoda-backend
```

### Cost Optimization

- Auto-stop/start is enabled by default
- Machines stop after 5 minutes of inactivity
- No charges when machines are stopped
- Consider using `fly-replay` header for multi-region deployments

---

## Access Your App

Open your browser to:
```
https://yoda-frontend.fly.dev
```

You can now access YODA from anywhere with **complete privacy**:
- ✅ Your LLM runs on YOUR infrastructure
- ✅ Ollama is NOT exposed to the internet (internal networking only)
- ✅ No third-party LLM services see your data
- ✅ All communication is encrypted (HTTPS)

---

## Cost Breakdown

Approximate monthly costs:

| Service | Configuration | Cost (with auto-stop) | Cost (always on) |
|---------|--------------|---------------------|------------------|
| Ollama | Performance-1x, auto-stop | ~$60-80 | ~$15 |
| Backend | 1GB RAM, shared CPU, auto-stop | ~$5-10 | ~$3 |
| Frontend | 512MB RAM, shared CPU, auto-stop | ~$3-5 | ~$1.50 |
| Volumes | 20GB storage | ~$2 | ~$2 |
| **Total** | | **~$70-97/month** | **~$21.50/month** |

*With auto-stop enabled, costs are reduced when idle (machines stop after 5 min)*

---

## Security Notes

- Ollama uses `.internal` networking - not accessible from internet ✅
- All secrets managed via Fly.io secrets (encrypted) ✅
- HTTPS enforced on all public endpoints ✅
- No third-party AI services = no data leakage ✅

You have complete control and privacy over your data!

---

## Clean Up

To remove all apps:

```bash
fly apps destroy yoda-frontend
fly apps destroy yoda-backend
fly apps destroy yoda-ollama
fly volumes destroy ollama_data --app yoda-ollama
```

---

## Next Steps After Deployment

1. **Pull your chosen model**: Use `fly ssh console --app yoda-ollama` then `ollama pull MODEL_NAME`
2. **Monitor usage**: Use `fly dashboard` to monitor resource usage
3. **Set up alerts**: Configure Fly.io alerts for downtime
4. **Scale if needed**: Adjust VM sizes based on usage
5. **Pull additional models**: Add more models to Ollama as needed

---

## Deployment Checklist

Before deploying, ensure:

1. ✅ Ollama is deployed and model is pulled
2. ✅ Backend secrets are set:
   ```bash
   fly secrets set \
     SUPABASE_URL="..." \
     SUPABASE_ANON_KEY="..." \
     SUPABASE_JWT_SECRET="..." \
     SUPABASE_SERVICE_KEY="..." \
     OLLAMA_BASE_URL="http://yoda-ollama.internal:11434" \
     FRONTEND_URL="https://yoda-frontend.fly.dev" \
     --app yoda-backend
   ```
3. ✅ Frontend is deployed with build args:
   ```bash
   cd app/frontend
   fly deploy \
     --build-arg VITE_API_BASE_URL="https://yoda-backend.fly.dev" \
     --build-arg VITE_SUPABASE_URL="your-supabase-url" \
     --build-arg VITE_SUPABASE_ANON_KEY="your-anon-key"
   ```
4. ✅ Verify health checks:
   ```bash
   curl https://yoda-backend.fly.dev/health
   curl https://yoda-frontend.fly.dev/health
   ```
5. ✅ Test CORS by accessing frontend and making API calls

---

## Additional Recommendations

1. **Consider using Fly.io internal networking** for backend-to-Ollama communication (already configured with `.internal` domain)

2. **Monitor memory usage** - Whisper model loading may require more than 1GB

3. **Set up log aggregation** for easier debugging:
   ```bash
   fly logs --app yoda-backend
   fly logs --app yoda-frontend
   ```

4. **Consider adding metrics/monitoring** for production deployments

---

*Last updated: 2025-12-04*

