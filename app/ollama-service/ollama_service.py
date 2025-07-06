from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import asyncio
from typing import AsyncGenerator
import json
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.2:1b"  # Default lightweight model
    system_prompt: str = "You are a helpful assistant."

class ChatResponse(BaseModel):
    response: str
    model: str

# Ollama API endpoint - use environment variable with fallback for local development
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

@app.get("/")
async def root():
    return {"message": "Ollama Chat Service is running"}

@app.get("/models")
async def list_models():
    """List available Ollama models"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch models from Ollama")
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Ollama: {e}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ollama(request: ChatRequest):
    """Send a message to Ollama and get response"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            ollama_request = {
                "model": request.model,
                "prompt": request.message,
                "system": request.system_prompt,
                "stream": False
            }
            
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json=ollama_request
            )
            
            if response.status_code == 200:
                result = response.json()
                return ChatResponse(
                    response=result.get("response", "No response received"),
                    model=request.model
                )
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail="Failed to get response from Ollama")
                
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Ollama: {e}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/chat/stream")
async def chat_with_ollama_stream(request: ChatRequest):
    """Send a message to Ollama and get streaming response"""
    from fastapi.responses import StreamingResponse
    
    async def generate_response():
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                ollama_request = {
                    "model": request.model,
                    "prompt": request.message,
                    "system": request.system_prompt,
                    "stream": True
                }
                
                async with client.stream(
                    'POST',
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json=ollama_request
                ) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_lines():
                            if chunk:
                                try:
                                    data = json.loads(chunk)
                                    if "response" in data:
                                        yield f"data: {json.dumps({'text': data['response']})}\n\n"
                                    if data.get("done", False):
                                        yield f"data: {json.dumps({'done': True})}\n\n"
                                        break
                                except json.JSONDecodeError:
                                    continue
                    else:
                        yield f"data: {json.dumps({'error': 'Failed to connect to Ollama'})}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

@app.post("/pull-model")
async def pull_model(model_name: str):
    """Pull a model from Ollama registry"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for model pulls
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/pull",
                json={"name": model_name}
            )
            
            if response.status_code == 200:
                return {"message": f"Model {model_name} pulled successfully"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to pull model {model_name}")
                
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Ollama: {e}")
        raise HTTPException(status_code=503, detail="Ollama service unavailable")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)