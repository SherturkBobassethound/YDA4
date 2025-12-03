# Complete YODA Deployment Guide (Private & Secure)

This guide deploys YODA with **maximum privacy** - all components run on your Fly.io infrastructure with no third-party LLM services.

## Prerequisites

1. **Fly.io CLI installed and authenticated**
   ```bash
   fly auth login
   ```

2. **Your Supabase credentials ready:**
   - SUPABASE_URL
   - SUPABASE_ANON_KEY
   - SUPABASE_JWT_SECRET
   - SUPABASE_SERVICE_KEY

## Deployment Order

### 1️⃣ Deploy Ollama (Private LLM)

```bash
cd ollama-fly

# Create volume for model storage
fly volumes create ollama_data --region sjc --size 20

# Deploy Ollama
fly deploy

# SSH into Ollama to pull your model
fly ssh console --app yoda-ollama

# Inside the SSH session, pull a model (choose one):
ollama pull phi           # Smallest (2.7GB) - fast but lower quality
# OR
ollama pull llama2        # Recommended (3.8GB) - balanced
# OR
ollama pull mistral       # Best quality (4.1GB) - slower

# Verify model is downloaded
ollama list

# Exit SSH
exit
```

**✅ Checkpoint:** Ollama is now running privately at `http://yoda-ollama.internal:11434`

---

### 2️⃣ Deploy Backend

```bash
cd ../app/backend

# Set your secrets (replace with your actual values)
fly secrets set \
  SUPABASE_URL="your-supabase-url" \
  SUPABASE_ANON_KEY="your-supabase-anon-key" \
  SUPABASE_JWT_SECRET="your-jwt-secret" \
  SUPABASE_SERVICE_KEY="your-service-key" \
  OLLAMA_BASE_URL="http://yoda-ollama.internal:11434"

# Deploy backend
fly deploy

# Get your backend URL
fly status --app yoda-backend
```

**✅ Checkpoint:** Note your backend URL (e.g., `yoda-backend.fly.dev`)

---

### 3️⃣ Deploy Frontend

```bash
cd ../frontend

# Set your environment variables (replace values)
fly secrets set \
  VITE_SUPABASE_URL="your-supabase-url" \
  VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" \
  VITE_API_BASE_URL="https://yoda-backend.fly.dev"

# Deploy frontend with build args
fly deploy \
  --build-arg VITE_SUPABASE_URL="your-supabase-url" \
  --build-arg VITE_SUPABASE_ANON_KEY="your-supabase-anon-key" \
  --build-arg VITE_API_BASE_URL="https://yoda-backend.fly.dev"
```

**✅ Checkpoint:** Your app is now live!

---

### 4️⃣ Verify Deployment

```bash
# Check backend health
curl https://yoda-backend.fly.dev/health

# Check frontend health
curl https://yoda-frontend.fly.dev/health

# View logs if needed
fly logs --app yoda-ollama
fly logs --app yoda-backend
fly logs --app yoda-frontend
```

---

## 🎉 Access Your App

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

## 💰 Cost Breakdown

Approximate monthly costs:

| Service | Configuration | Cost |
|---------|--------------|------|
| Ollama | 8GB RAM, 2 CPU (performance), auto-stop | ~$60-80 |
| Backend | 1GB RAM, 1 CPU (shared), auto-stop | ~$5-10 |
| Frontend | 512MB RAM, 1 CPU (shared), auto-stop | ~$3-5 |
| Volumes | 20GB storage | ~$2 |
| **Total** | | **~$70-97/month** |

*With auto-stop enabled, costs are reduced when idle (machines stop after 5 min)*

---

## 📊 Monitoring

```bash
# View real-time logs
fly logs --app yoda-backend

# Check status
fly status --app yoda-backend

# Open dashboard
fly dashboard --app yoda-backend
```

---

## 🔄 Updating Your Deployment

When you make code changes:

```bash
# Update backend
cd app/backend
fly deploy

# Update frontend
cd ../frontend
fly deploy
```

---

## 🛠️ Troubleshooting

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

### Backend can't connect to Ollama
- Verify `OLLAMA_BASE_URL` is set to `http://yoda-ollama.internal:11434`
- Check both apps are in the same region (`sjc`)
- View backend logs: `fly logs --app yoda-backend`

### Frontend can't reach backend
- Verify `VITE_API_BASE_URL` matches your backend URL
- Check CORS is configured correctly
- View frontend logs: `fly logs --app yoda-frontend`

---

## 🗑️ Clean Up

To remove all apps:

```bash
fly apps destroy yoda-frontend
fly apps destroy yoda-backend
fly apps destroy yoda-ollama
fly volumes destroy ollama_data --app yoda-ollama
```

---

## 🔐 Security Notes

- Ollama uses `.internal` networking - not accessible from internet ✅
- All secrets managed via Fly.io secrets (encrypted) ✅
- HTTPS enforced on all public endpoints ✅
- No third-party AI services = no data leakage ✅

You have complete control and privacy over your data!
