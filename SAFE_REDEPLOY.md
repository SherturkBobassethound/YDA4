# Safe Redeploy Guide - Preserving Data

This guide shows how to redeploy Ollama and Backend without losing any data (models, volumes, secrets).

## What Gets Preserved ✅

- **Volumes**: All data in mounted volumes (like `ollama_data` with your models)
- **Secrets**: All environment variables/secrets set via `fly secrets set`
- **Machine state**: Running machines stay running (if configured)

## What Gets Updated 🔄

- **Code**: New Docker image built from your Dockerfile
- **Configuration**: Changes in `fly.toml` (ports, memory, auto-stop settings, etc.)
- **Dependencies**: Updated packages/libraries if Dockerfile changed

## Safe Redeploy Steps

### 1. Verify Current State (Optional but Recommended)

```bash
# Check Ollama models before redeploy
fly ssh console --app yoda-ollama
ollama list
exit

# Check volumes
fly volumes list --app yoda-ollama

# Check secrets (won't show values, just names)
fly secrets list --app yoda-ollama
fly secrets list --app yoda-backend
```

### 2. Redeploy Ollama

```bash
cd ollama-fly

# Redeploy - this updates config but preserves volumes
fly deploy --app yoda-ollama
```

**What happens:**
- ✅ Volume `ollama_data` stays attached and all models remain
- ✅ Secrets (like `OLLAMA_HOST`) remain unchanged
- 🔄 New container image is built/deployed
- 🔄 Configuration from `fly.toml` is applied (auto-stop settings, etc.)

### 3. Redeploy Backend

```bash
cd ../app/backend

# Redeploy - this updates config but preserves secrets
fly deploy --app yoda-backend
```

**What happens:**
- ✅ All secrets remain (SUPABASE_URL, OLLAMA_BASE_URL, etc.)
- 🔄 New container image is built/deployed
- 🔄 Configuration from `fly.toml` is applied

### 4. Verify After Redeploy

```bash
# Verify Ollama models are still there
fly ssh console --app yoda-ollama
ollama list
exit

# Check backend health
curl https://yoda-backend.fly.dev/health

# Check both apps are running
fly status --app yoda-ollama
fly status --app yoda-backend
```

## Important Notes

### Volumes Are Never Deleted by `fly deploy`
- The `ollama_data` volume persists across all deployments
- Models stored in `/root/.ollama` remain intact
- Only way to lose volume data is explicit `fly volumes destroy`

### Secrets Are Never Deleted by `fly deploy`
- All secrets set via `fly secrets set` remain
- They're stored separately from the deployment
- Only way to remove is explicit `fly secrets unset`

### Zero-Downtime Deployment
Fly.io performs rolling deployments:
- New machines are created with new config
- Old machines stay running until new ones are healthy
- Then old machines are stopped
- Your app stays available during the process

## Troubleshooting

### If Models Seem Missing After Redeploy

```bash
# Check volume is still attached
fly volumes list --app yoda-ollama

# SSH in and check mount point
fly ssh console --app yoda-ollama
ls -la /root/.ollama
df -h /root/.ollama
exit
```

### If Secrets Seem Missing

```bash
# List secrets to verify they exist
fly secrets list --app yoda-backend

# If missing, re-set them (they won't be lost on next deploy)
fly secrets set KEY="value" --app yoda-backend
```

### If You Want to Force a Clean Deploy (NOT RECOMMENDED)

Only if you really need to start fresh (will lose data):

```bash
# This destroys machines but NOT volumes
fly machine destroy --app yoda-ollama

# Then redeploy
fly deploy --app yoda-ollama
```

**Warning**: This destroys machines but volumes remain. Models will still be there when new machines start.

## Quick Commands

```bash
# Redeploy both apps
cd ollama-fly && fly deploy --app yoda-ollama
cd ../app/backend && fly deploy --app yoda-backend

# Check status
fly status --app yoda-ollama
fly status --app yoda-backend

# View logs
fly logs --app yoda-ollama
fly logs --app yoda-backend
```

