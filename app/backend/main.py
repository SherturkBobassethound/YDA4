from fastapi import FastAPI, UploadFile, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import yt_dlp
import whisper
import requests
import tempfile
import os
from pathlib import Path
import logging
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.embeddings import HuggingFaceEmbeddings

from services.text_splitter import TextSplitter
from services.user_manager import UserIdentifier
from services.pod_fetcher import PodFetcher
from services.supabase_client import supabase, get_user_supabase_client
from db.qdrant_db import QdrantDB
from auth import get_current_user

# Initialize components
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Get service URLs from environment variables with fallbacks for local development
QDRANT_URL = os.getenv('QDRANT_URL', 'http://localhost:6333')
OLLAMA_API_URL = os.getenv('OLLAMA_API_URL', 'http://localhost:8001')

# Initialize services
text_splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

# Helper function to get user-specific vector DB
def get_user_vector_db(user_id: str) -> QdrantDB:
    """Get or create a QdrantDB instance for the specific user"""
    collection_name = UserIdentifier.get_collection_name(user_id)
    return QdrantDB(collection_name=collection_name, embedding_model=embedding_model, client_url=QDRANT_URL)

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Improved CORS configuration
origins = [
    "http://localhost",
    "http://localhost:80",
    "http://localhost:3000",
    "http://localhost:5173",  # Vite dev server
    "http://frontend",  # Docker service name
    "http://frontend:80"
]

# Only allow all origins in development
if os.getenv('ENVIRONMENT') == 'development':
    origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Load Whisper model
try:
    model = whisper.load_model("base")
    logger.info("Whisper model loaded successfully")
except Exception as e:
    logger.error(f"Error loading Whisper model: {str(e)}")
    raise

class TranscriptionRequest(BaseModel):
    youtube_url: Optional[str] = None
    podcast_url: Optional[str] = None

class URLRequest(BaseModel):
    url: str

class ChatRequest(BaseModel):
    message: str
    context: Optional[str] = None  # For passing transcription context
    model: Optional[str] = "llama3.2:1b"  # Default model

class SourceCreate(BaseModel):
    title: str
    url: str
    type: str  # 'youtube' or 'podcast'

def download_youtube_audio(url: str) -> dict:
    """Download audio from YouTube video and save to temporary file

    Returns:
        dict: {'audio_file': str, 'title': str}
    """
    logger.info(f"Starting download of YouTube video: {url}")
    
    # First, try to get available formats to make an informed decision
    def get_available_formats(video_url):
        """Get available formats for the video"""
        format_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'noplaylist': True,
        }
        try:
            with yt_dlp.YoutubeDL(format_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info.get('formats', [])
        except Exception as e:
            logger.warning(f"Could not get format info: {str(e)}")
            return []
    
    # Get available formats
    available_formats = get_available_formats(url)
    logger.info(f"Found {len(available_formats)} available formats")
    
    # Build format selector based on available formats
    format_selector = 'bestaudio/best/worst'
    if available_formats:
        # Check if we have audio-only formats
        audio_formats = [f for f in available_formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if audio_formats:
            # Prefer specific audio formats if available
            format_selector = 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio[ext=mp3]/bestaudio/best/worst'
        else:
            # Fall back to video formats if no audio-only available
            format_selector = 'best[height<=480]/best/worst'
    
    ydl_opts = {
        'format': format_selector,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': '%(id)s.%(ext)s',
        'noplaylist': True,
        'writethumbnail': False,
        'writeinfojson': False,
        'ignoreerrors': False,
        'no_warnings': False,
        # Updated extractor args for current yt-dlp version
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web', 'ios'],
                'skip': ['dash', 'hls']
            }
        }
    }
    
    try:
        logger.info("Attempting primary download configuration...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_file = f"{info['id']}.mp3"
            title = info.get('title', 'Unknown Title')
            logger.info(f"Successfully downloaded audio: {audio_file}")
            return {'audio_file': audio_file, 'title': title}
    except Exception as e:
        logger.error(f"Primary download failed: {str(e)}")
        logger.info("Primary download failed, attempting fallback...")
        
        # Try fallback configuration with more permissive settings
        logger.info("Trying fallback configuration...")
        fallback_opts = {
            'format': 'best/worst',  # More permissive format selection
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # Lower quality for compatibility
            }],
            'outtmpl': '%(id)s.%(ext)s',
            'noplaylist': True,
            'ignoreerrors': True,
            'no_warnings': True,
            # Updated extractor args for current yt-dlp version
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web', 'ios', 'tv_embedded'],
                    'skip': ['dash', 'hls'],
                    'include_live_chat': False
                }
            },
            # Try different user agents
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
            }
        }
        
        try:
            logger.info("Attempting fallback download configuration...")
            with yt_dlp.YoutubeDL(fallback_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                audio_file = f"{info['id']}.mp3"
                title = info.get('title', 'Unknown Title')
                logger.info(f"Successfully downloaded audio with fallback: {audio_file}")
                return {'audio_file': audio_file, 'title': title}
        except Exception as fallback_error:
            logger.error(f"Fallback download also failed: {str(fallback_error)}")
            
            # Try third fallback: download video and extract audio
            logger.info("Trying video-to-audio conversion fallback...")
            video_fallback_opts = {
                'format': 'worst[height<=480]/worst',  # Get worst video quality
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '128',
                }],
                'outtmpl': '%(id)s.%(ext)s',
                'noplaylist': True,
                'ignoreerrors': True,
                'no_warnings': True,
                # Updated extractor args for current yt-dlp version
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android', 'web', 'ios', 'tv_embedded'],
                        'skip': ['dash', 'hls'],
                        'include_live_chat': False
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
                }
            }
            
            try:
                logger.info("Attempting video-to-audio conversion fallback...")
                with yt_dlp.YoutubeDL(video_fallback_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    audio_file = f"{info['id']}.mp3"
                    title = info.get('title', 'Unknown Title')
                    logger.info(f"Successfully downloaded audio with video fallback: {audio_file}")
                    return {'audio_file': audio_file, 'title': title}
            except Exception as video_fallback_error:
                logger.error(f"Video fallback also failed: {str(video_fallback_error)}")
                
                # Final fallback: try with the most permissive settings possible
                logger.info("Trying final permissive fallback...")
                final_fallback_opts = {
                    'format': 'worst',  # Most permissive format selection
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio',
                        'preferredcodec': 'mp3',
                        'preferredquality': '96',  # Very low quality for maximum compatibility
                    }],
                    'outtmpl': '%(id)s.%(ext)s',
                    'noplaylist': True,
                    'ignoreerrors': True,
                    'no_warnings': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android', 'web', 'ios', 'tv_embedded', 'mweb'],
                            'skip': ['dash', 'hls'],
                            'include_live_chat': False
                        }
                    },
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36'
                    }
                }
                
                try:
                    logger.info("Attempting final permissive fallback...")
                    with yt_dlp.YoutubeDL(final_fallback_opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                        audio_file = f"{info['id']}.mp3"
                        title = info.get('title', 'Unknown Title')
                        logger.info(f"Successfully downloaded audio with final fallback: {audio_file}")
                        return {'audio_file': audio_file, 'title': title}
                except Exception as final_error:
                    logger.error(f"Final fallback also failed: {str(final_error)}")
                    raise HTTPException(status_code=400, detail=f"Failed to download YouTube video after all attempts. Primary error: {str(e)}. Fallback error: {str(fallback_error)}. Video fallback error: {str(video_fallback_error)}. Final fallback error: {str(final_error)}")

def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio file using Whisper model"""
    logger.info(f"Starting transcription of audio file: {audio_path}")
    try:
        result = model.transcribe(audio_path)
        logger.info("Transcription completed successfully")
        return result["text"]
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to transcribe audio: {str(e)}")

def generate_summary_ollama(text: str, model_name: str = "llama3.2:1b") -> str:
    """Generate summary using Ollama through the API service"""
    logger.info(f"Starting summary generation with Ollama model: {model_name}")
    try:
        # Truncate very long texts to avoid memory issues
        max_length = 8000  # Adjust based on your needs
        if len(text) > max_length:
            text = text[:max_length] + "... [truncated for processing]"
            logger.info(f"Text truncated to {max_length} characters for processing")
        
        response = requests.post(
            f"{OLLAMA_API_URL}/chat",
            json={
                "message": f"Please provide a concise summary of the following text, highlighting the key learnings and main points:\n\n{text}",
                "model": model_name,
                "system_prompt": "You are a helpful assistant that provides clear, concise summaries."
            },
            timeout=300  # 5 minute timeout for summary generation
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Summary generated successfully with Ollama")
        return result["response"]
    except requests.exceptions.Timeout:
        logger.error("Timeout while generating summary with Ollama")
        raise HTTPException(status_code=408, detail="Summary generation timed out. The content might be too long.")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama API service.")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama API service. Please make sure the service is running.")
    except Exception as e:
        logger.error(f"Error generating summary with Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

def chat_with_ollama(message: str, vector_db: QdrantDB, context: str = None, model_name: str = "llama3.2:1b") -> str:
    """Chat with Ollama model through the API service, with enhanced context from vector DB"""
    logger.info(f"Starting chat with Ollama model: {model_name}")

    # Enhanced context retrieval using vector database
    enhanced_context = context
    try:
        if hasTranscription := bool(context):  # If we have a transcription context
            # Search vector DB for relevant chunks
            search_results = vector_db.search(message, k=5)
            if search_results:
                # Format the search results into a context string
                vector_context_parts = []
                for i, doc in enumerate(search_results, 1):
                    vector_context_parts.append(f"Relevant excerpt {i}: {doc.page_content}")
                
                vector_context = "\n\n".join(vector_context_parts)
                
                # Combine original context with vector search results
                enhanced_context = f"Based on these relevant excerpts from the content:\n\n{vector_context}\n\n"
                logger.info(f"Enhanced context with {len(search_results)} relevant chunks from vector DB")
            else:
                logger.info("No relevant chunks found in vector DB, using full transcript context")
    except Exception as e:
        logger.warning(f"Vector DB search failed, falling back to original context: {str(e)}")
        enhanced_context = context
    
    try:
        if enhanced_context:
            # Limit context size to avoid token limits
            max_context = 4000  # Increased for better context
            if len(enhanced_context) > max_context:
                enhanced_context = enhanced_context[:max_context] + "... [truncated]"
            prompt = f"{enhanced_context}\n\nUser question: {message}\n\nPlease provide a helpful response based on the content above."
        else:
            prompt = message
            
        response = requests.post(
            f"{OLLAMA_API_URL}/chat",
            json={
                "message": prompt,
                "model": model_name,
                "system_prompt": "You are a helpful assistant that answers questions accurately and concisely based on the provided context."
            },
            timeout=120  # 2 minute timeout for chat
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Chat response generated successfully")
        return result["response"]
    except requests.exceptions.Timeout:
        logger.error("Timeout while generating chat response")
        raise HTTPException(status_code=408, detail="Response generation timed out. Please try a simpler question.")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama API service for chat")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama API service. Please make sure the service is running.")
    except Exception as e:
        logger.error(f"Error in chat with Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chat response: {str(e)}")

def store_transcript_in_vector_db(transcript: str, source: str, url: str, user_id: str, vector_db: QdrantDB):
    """
    Splits a transcript into chunks and inserts them into the Qdrant vector DB
    with metadata for retrieval.
    """
    logger.info("Splitting transcript into chunks for vector DB storage...")
    chunks = text_splitter.split_text(transcript)

    texts = []
    metadatas = []

    for i, chunk in enumerate(chunks):
        texts.append(chunk)
        metadatas.append({
            "source": source,
            "url": url,
            "chunk_index": i,
            "user_id": user_id,
            "timestamp": f"{i * 30}s"  # Approximate timestamp for chunks
        })

    if texts:
        vector_db.vectorstore.add_texts(texts=texts, metadatas=metadatas)
        logger.info(f"Inserted {len(texts)} chunks into vector DB for {source} at {url}")
    else:
        logger.warning("No chunks were created from transcript; skipping vector DB insert.")

@app.get("/models")
async def get_models():
    """Get available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_API_URL}/models", timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=503, detail="Could not fetch available models")

@app.post("/process-youtube")
async def process_youtube(request: TranscriptionRequest, user: dict = Depends(get_current_user)):
    """Process YouTube video: download audio, transcribe, and summarize"""
    if not request.youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    logger.info(f"Processing YouTube URL: {request.youtube_url} for user: {user['id']}")
    audio_file = None
    video_title = "Unknown Title"

    # Get user-specific vector database
    vector_db = get_user_vector_db(user['id'])

    try:
        # Download audio from YouTube
        download_result = download_youtube_audio(request.youtube_url)
        audio_file = download_result['audio_file']
        video_title = download_result['title']

        # Transcribe audio
        transcription = transcribe_audio(audio_file)

        # Store transcript in vector database
        store_transcript_in_vector_db(transcription, source="youtube", url=request.youtube_url, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")

        # Generate summary using Ollama
        summary = generate_summary_ollama(transcription)

        # Save source to database using user's token for RLS
        try:
            user_supabase = get_user_supabase_client(user['token'])
            user_supabase.table('sources').insert({
                "user_id": user['id'],
                "title": video_title,
                "url": request.youtube_url,
                "type": "youtube"
            }).execute()
            logger.info(f"Saved source to database: {video_title}")
        except Exception as e:
            # Don't fail the whole request if source saving fails (might be duplicate)
            logger.warning(f"Could not save source to database: {str(e)}")

        return {
            "title": video_title,
            "transcription": transcription,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error in process_youtube: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary audio file
        if audio_file and os.path.exists(audio_file):
            try:
                os.remove(audio_file)
                logger.info(f"Cleaned up temporary file: {audio_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {str(e)}")

@app.post("/process-audio")
async def process_audio(file: UploadFile, user: dict = Depends(get_current_user)):
    """Process uploaded audio file: transcribe and summarize"""
    if not file:
        raise HTTPException(status_code=400, detail="Audio file is required")

    logger.info(f"Processing uploaded audio file: {file.filename} for user: {user['id']}")
    temp_path = None

    # Get user-specific vector database
    vector_db = get_user_vector_db(user['id'])

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            logger.info(f"Saved temporary file: {temp_path}")

        # Transcribe audio
        transcription = transcribe_audio(temp_path)

        # Store transcript in vector database
        store_transcript_in_vector_db(transcription, source="audio_upload", url=file.filename, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")
        
        # Generate summary using Ollama
        summary = generate_summary_ollama(transcription)
        
        return {
            "transcription": transcription,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error in process_audio: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                logger.info(f"Cleaned up temporary file: {temp_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file: {str(e)}")
    
@app.post("/process-podcast")
async def process_podcast(request: TranscriptionRequest, user: dict = Depends(get_current_user)):
    """Process podcast: download episode (audio or transcript), transcribe if needed, and summarize"""
    if not request.podcast_url:
        raise HTTPException(status_code=400, detail="Podcast URL is required")

    logger.info(f"Processing podcast URL: {request.podcast_url} for user: {user['id']}")
    fetcher = PodFetcher()
    file_path = None

    # Get user-specific vector database
    vector_db = get_user_vector_db(user['id'])

    try:
        # Download podcast file
        info = fetcher.fetch(request.podcast_url)
        file_path = info["filepath"]
        episode_title = info.get("episode_title", "Unknown Podcast")
        podcast_name = info.get("podcast_name", "")

        # Combine podcast name and episode title for display
        if podcast_name and episode_title:
            full_title = f"{podcast_name}: {episode_title}"
        else:
            full_title = episode_title or podcast_name or "Unknown Podcast"

        logger.info(f"Downloaded {info['download_type']} to {file_path}")

        # Handle transcription
        if info["download_type"] == "transcript":
            with open(file_path, "r", encoding="utf-8") as f:
                transcription = f.read()
            logger.info("Loaded transcript from file")
        else:
            transcription = transcribe_audio(file_path)
            logger.info("Audio file transcribed successfully")

        # Store transcript in vector database
        store_transcript_in_vector_db(transcription, source="podcast", url=request.podcast_url, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")

        # Generate summary
        summary = generate_summary_ollama(transcription)
        logger.info("Summary generated successfully")

        # Save source to database using user's token for RLS
        try:
            user_supabase = get_user_supabase_client(user['token'])
            user_supabase.table('sources').insert({
                "user_id": user['id'],
                "title": full_title,
                "url": request.podcast_url,
                "type": "podcast"
            }).execute()
            logger.info(f"Saved source to database: {full_title}")
        except Exception as e:
            # Don't fail the whole request if source saving fails (might be duplicate)
            logger.warning(f"Could not save source to database: {str(e)}")

        return {
            "title": full_title,
            "transcription": transcription,
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error in process_podcast: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up file: {str(e)}")
    
@app.post("/process-url")
async def process_url(request: URLRequest, user: dict = Depends(get_current_user)):
    url = request.url.strip()

    if "youtube.com" in url or "youtu.be" in url:
        logger.info("Detected YouTube URL")
        transcription_request = TranscriptionRequest(youtube_url=url)
        return await process_youtube(transcription_request, user)

    elif "podcasts.apple.com" in url:
        logger.info("Detected Apple Podcast URL")
        transcription_request = TranscriptionRequest(podcast_url=url)
        return await process_podcast(transcription_request, user)

    else:
        logger.warning("Unrecognized URL format")
        raise HTTPException(status_code=400, detail="Unsupported URL type")

@app.post("/chat")
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    """Enhanced chat endpoint with vector database integration"""
    try:
        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'])

        response = chat_with_ollama(request.message, vector_db, request.context, request.model)
        return {"response": response}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_transcripts(query: str, k: int = 5, user: dict = Depends(get_current_user)):
    """Search through stored transcripts using vector similarity"""
    try:
        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'])

        results = vector_db.search(query, k=k)
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata if hasattr(doc, 'metadata') else {}
            })
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources")
async def get_sources(user: dict = Depends(get_current_user)):
    """Get all sources for the authenticated user"""
    try:
        user_supabase = get_user_supabase_client(user['token'])
        result = user_supabase.table('sources').select('*').eq('user_id', user['id']).order('created_at', desc=True).execute()

        # Format the response to match frontend expectations
        sources = []
        for item in result.data:
            sources.append({
                "id": item['id'],
                "title": item['title'],
                "url": item['url'],
                "type": item['type'],
                "addedAt": item['created_at']
            })

        return {"sources": sources}
    except Exception as e:
        logger.error(f"Error fetching sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sources")
async def create_source(source: SourceCreate, user: dict = Depends(get_current_user)):
    """Create a new source for the authenticated user"""
    try:
        user_supabase = get_user_supabase_client(user['token'])
        result = user_supabase.table('sources').insert({
            "user_id": user['id'],
            "title": source.title,
            "url": source.url,
            "type": source.type
        }).execute()

        # Format the response
        item = result.data[0]
        return {
            "id": item['id'],
            "title": item['title'],
            "url": item['url'],
            "type": item['type'],
            "addedAt": item['created_at']
        }
    except Exception as e:
        logger.error(f"Error creating source: {str(e)}")
        # Handle duplicate URL error gracefully
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(status_code=409, detail="This source already exists")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sources/{source_id}")
async def delete_source(source_id: str, user: dict = Depends(get_current_user)):
    """Delete a source and its associated vector data"""
    try:
        # Use user's token for RLS
        user_supabase = get_user_supabase_client(user['token'])
        
        # First, verify the source belongs to the user
        result = user_supabase.table('sources').select('*').eq('id', source_id).eq('user_id', user['id']).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Source not found")

        source = result.data[0]
        source_url = source['url']

        # Delete from Qdrant vector database first
        try:
            # Get user-specific vector database
            vector_db = get_user_vector_db(user['id'])

            # Delete all vectors associated with this URL
            vector_db.delete_by_url(source_url)
            logger.info(f"Deleted vectors for URL: {source_url} from user's vector database")
        except Exception as e:
            logger.error(f"Error deleting vectors for source {source_id}: {str(e)}")
            # Continue with Supabase deletion even if vector deletion fails
            # This prevents orphaned database records

        # Delete from Supabase
        user_supabase.table('sources').delete().eq('id', source_id).eq('user_id', user['id']).execute()

        logger.info(f"Deleted source {source_id} for user {user['id']}")

        return {"success": True, "message": "Source and associated vectors deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies service connections"""
    status = {
        "status": "healthy",
        "whisper": "loaded",
        "ollama_api": "disconnected",
        "qdrant": "disconnected"
    }
    
    try:
        # Check if Ollama API service is running
        response = requests.get(f"{OLLAMA_API_URL}/models", timeout=5)
        status["ollama_api"] = "connected" if response.status_code == 200 else "disconnected"
    except Exception as e:
        logger.warning(f"Ollama API health check failed: {str(e)}")
    
    try:
        # Check if Qdrant is running
        response = requests.get(f"{QDRANT_URL}/", timeout=5)
        status["qdrant"] = "connected" if response.status_code == 200 else "disconnected"
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {str(e)}")
    
    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)