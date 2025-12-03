# Deploy Ollama on Fly.io (Private & Secure)

This guide deploys Ollama on Fly.io with **internal networking only** - keeping your LLM completely private.

## Step 1: Deploy Ollama

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

## Step 2: Pull Your LLM Model

SSH into your Ollama machine to download the model:

```bash
# Connect to the Ollama machine
fly ssh console --app yoda-ollama

# Inside the machine, pull your desired model (e.g., llama2, mistral, phi)
ollama pull llama2

# Or for a smaller model:
# ollama pull phi

# Verify the model is ready
ollama list

# Exit the SSH session
exit
```

## Step 3: Verify Ollama is Running

Check that Ollama is accessible internally:

```bash
# Check app status
fly status --app yoda-ollama

# View logs
fly logs --app yoda-ollama
```

## Model Options

Choose based on your needs:

- **phi** (2.7GB) - Fast, good for testing, lower quality
- **llama2** (3.8GB) - Balanced performance and quality
- **mistral** (4.1GB) - Better quality, slightly slower
- **codellama** (3.8GB) - Optimized for code tasks

## Internal URL

Your backend will use: `http://yoda-ollama.internal:11434`

This URL is **only accessible from your other Fly.io apps**, not from the public internet. Maximum privacy!

## Cost Estimate

- 8GB RAM performance machine: ~$60-80/month
- Auto-stop enabled: Saves money when idle (stops after 5 min)
- Volume storage (20GB): ~$2/month

## Next Steps

After Ollama is deployed and your model is pulled, proceed to deploy your backend with:

```bash
OLLAMA_BASE_URL="http://yoda-ollama.internal:11434"
```
