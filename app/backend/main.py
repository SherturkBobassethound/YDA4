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
from langchain_huggingface import HuggingFaceEmbeddings

from services.text_splitter import TextSplitter
from services.pod_fetcher import PodFetcher
from services.transcript_fetcher import TranscriptFetcher
from services.supabase_client import supabase, get_user_supabase_client
from db.supabase_vector_db import SupabaseVectorDB
from services.user_preferences import UserPreferencesService
from auth import get_current_user
from config.model_config import get_max_input_chars, get_model_context_window

# Initialize components
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# Get Ollama base URL from environment variables with fallbacks for local development
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

# Initialize services
text_splitter = TextSplitter(chunk_size=1000, chunk_overlap=200)

# Helper function to get user-specific vector DB
def get_user_vector_db(user_id: str, user_token: str) -> SupabaseVectorDB:
    """Get a SupabaseVectorDB instance for the specific user"""
    supabase_client = get_user_supabase_client(user_token)
    return SupabaseVectorDB(user_id=user_id, embedding_model=embedding_model, supabase_client=supabase_client)

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

class PreferencesUpdate(BaseModel):
    preferred_model: str

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
    """Generate summary using Ollama with model-specific context windows"""
    logger.info(f"Starting summary generation with Ollama model: {model_name}")
    try:
        # Get model-specific max input size
        max_chars = get_max_input_chars(model_name)
        original_length = len(text)

        # Truncate if transcript exceeds model's context window
        if len(text) > max_chars:
            text = text[:max_chars]
            logger.warning(f"Transcript truncated from {original_length} to {max_chars} chars for {model_name} (context window limit)")

        # Enhanced summarization prompt with structured format
        prompt = f"""Analyze and summarize the following podcast/video transcript.

TRANSCRIPT:
{text}

---

Provide a comprehensive summary with the following structure:

## OVERVIEW
In 2-3 sentences, describe:
- What is the main topic of this content?
- What is the key thesis or central argument?

## KEY POINTS
List 4-6 main ideas discussed (use bullet points):
- Focus on the most important concepts and arguments
- Include relevant facts, statistics, or examples when notable
- Present in logical order

## NOTABLE INSIGHTS
Highlight interesting takeaways:
- Memorable quotes or powerful statements
- Unique perspectives or counterintuitive points
- Actionable recommendations or advice (if any)

Keep the summary detailed enough to understand the content without watching/listening, but concise enough to read in 2-3 minutes."""

        # Enhanced system message for summarization
        system_message = """You are an expert at analyzing and summarizing long-form content such as podcasts, videos, and lectures.

Your summaries are:
- Comprehensive yet concise
- Well-structured with clear sections
- Focused on key insights and actionable takeaways
- Accurate to the source material without adding interpretation or external knowledge
- Written in clear, accessible language

Follow the requested format exactly and ensure all important information is captured."""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "system": system_message,
                "stream": False
            },
            timeout=300  # 5 minute timeout for summary generation
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Summary generated successfully with Ollama")
        return result.get("response", "No response received")
    except requests.exceptions.Timeout:
        logger.error("Timeout while generating summary with Ollama")
        raise HTTPException(status_code=408, detail="Summary generation timed out. The content might be too long.")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama service.")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service. Please make sure the service is running.")
    except Exception as e:
        logger.error(f"Error generating summary with Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate summary: {str(e)}")

def chat_with_ollama(message: str, vector_db: SupabaseVectorDB, context: str = None, model_name: str = "llama3.2:1b") -> dict:
    """Chat with RAG - answers questions using retrieved context from user's sources

    Returns:
        dict: {
            'response': str,  # LLM's answer
            'sources': dict   # Mapping of citation numbers to {title, content}
        }
    """
    logger.info(f"Starting RAG chat with Ollama model: {model_name}")

    # RAG: Retrieve relevant chunks from vector DB
    enhanced_context = None
    source_map = {}  # Track source titles for citations

    try:
        logger.info(f"Searching vector DB for question: {message}")
        # Calculate dynamic K based on model's context window
        # Larger models can handle more chunks for better context
        max_context_chars = get_max_input_chars(model_name) * 0.65  # Reserve 65% for context
        dynamic_k = min(20, max(5, int(max_context_chars // 1000)))  # Min 5, max 20 chunks
        logger.info(f"Using dynamic k={dynamic_k} for model {model_name} (max_context: {max_context_chars} chars)")

        # Search vector DB for relevant chunks from ALL user's sources
        search_results = vector_db.search(message, k=dynamic_k)

        if search_results:
            # First, collect unique source_ids and fetch their titles from the database
            source_ids = set()
            for doc in search_results:
                metadata = doc.get('metadata', {})
                source_id = metadata.get('source_id')
                if source_id:
                    source_ids.add(source_id)

            # Fetch source titles from database
            source_titles_map = {}  # source_id -> title
            if source_ids:
                try:
                    sources_result = vector_db.supabase.table('sources').select('id, title').in_('id', list(source_ids)).execute()
                    for source in sources_result.data:
                        source_titles_map[source['id']] = source['title']
                except Exception as e:
                    logger.warning(f"Could not fetch source titles: {str(e)}")

            # Format with numbered citations and track source titles
            context_parts = []
            for i, doc in enumerate(search_results, 1):
                # Get source metadata
                metadata = doc.get('metadata', {})
                source_id = metadata.get('source_id', 'unknown')

                # Get the actual source title from our lookup
                source_title = source_titles_map.get(source_id, f"Unknown Source ({metadata.get('source', 'unknown')})")

                # Store source mapping for reference (with title and content for UI)
                source_map[str(i)] = {
                    "title": source_title,
                    "content": doc['page_content']
                }

                # Format: [1] Source: Title\nContent
                context_parts.append(
                    f"[{i}] Source: {source_title}\n{doc['page_content']}"
                )

            vector_context = "\n\n".join(context_parts)
            enhanced_context = vector_context
            logger.info(f"Retrieved {len(search_results)} relevant chunks from vector DB")
        else:
            logger.info("No relevant chunks found in vector DB")
            # If no vector search results and context provided, use that as fallback
            if context:
                enhanced_context = context
                logger.info("Using provided context as fallback")
    except Exception as e:
        logger.warning(f"Vector DB search failed: {str(e)}")
        # If vector search fails and context provided, use that as fallback
        if context:
            enhanced_context = context
            logger.warning("Falling back to provided context")

    try:
        if enhanced_context:
            # Use model-specific context window for better utilization
            max_context_chars = get_max_input_chars(model_name) * 0.65  # Reserve 65% for context, 35% for response
            if len(enhanced_context) > max_context_chars:
                enhanced_context = enhanced_context[:max_context_chars] + "\n\n... [Context truncated due to length]"

            # Enhanced RAG prompt with citation instructions
            prompt = f"""RELEVANT CONTENT FROM USER'S SOURCES:

{enhanced_context}

---

USER QUESTION: {message}

INSTRUCTIONS:
- Answer the question using ONLY the information provided in the content above
- Not all provided sources may be relevant - only cite those that actually help answer the question
- Cite your sources using [1], [2], etc. when referencing specific information
- If none of the sources are relevant, clearly state that the question cannot be answered from the available content
- If the content doesn't fully answer the question, explain what you CAN answer based on available sources and what information is missing
- When multiple sources discuss the same topic, compare and synthesize the information
- Be conversational but accurate"""

            # Enhanced system message for RAG chat
            system_message = """You are a helpful AI assistant that answers questions about the user's podcast and video library.

CRITICAL RULES:
1. ONLY use information from the provided content excerpts - do not use external knowledge
2. ALWAYS cite sources using [1], [2], etc. when making claims or referencing information
3. If you're unsure or the content doesn't contain enough information, say so clearly
4. Never make up information or fill in gaps with assumptions
5. When multiple sources discuss the same topic, acknowledge different perspectives

Your goal is to help users understand and recall information from their saved content."""
        else:
            # No sources available
            prompt = f"""USER QUESTION: {message}

I don't have any relevant sources in your library to answer this question. Please upload podcasts, videos, or audio files that contain information about this topic."""

            system_message = """You are a helpful assistant that only answers based on the user's uploaded content.
When no relevant content is available, politely explain that the user needs to upload sources covering this topic."""

        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "system": system_message,
                "stream": False
            },
            timeout=120  # 2 minute timeout for chat
        )
        response.raise_for_status()
        result = response.json()
        logger.info("Chat response generated successfully")

        # Return both the response and source citations
        return {
            "response": result.get("response", "No response received"),
            "sources": source_map
        }
    except requests.exceptions.Timeout:
        logger.error("Timeout while generating chat response")
        raise HTTPException(status_code=408, detail="Response generation timed out. Please try a simpler question.")
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama service for chat")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service. Please make sure the service is running.")
    except Exception as e:
        logger.error(f"Error in chat with Ollama: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to generate chat response: {str(e)}")

def store_transcript_in_vector_db(transcript: str, source_id: str, source: str, url: str, user_id: str, vector_db: SupabaseVectorDB):
    """
    Splits a transcript into chunks and inserts them into the Supabase vector DB
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
            "source_id": source_id,
            "timestamp": f"{i * 30}s"  # Approximate timestamp for chunks
        })

    if texts:
        vector_db.add_texts(texts=texts, source_id=source_id, metadata=metadatas)
        logger.info(f"Inserted {len(texts)} chunks into vector DB for {source} at {url}")
    else:
        logger.warning("No chunks were created from transcript; skipping vector DB insert.")

@app.get("/models")
async def get_models():
    """Get available Ollama models"""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error("Cannot connect to Ollama service")
        raise HTTPException(status_code=503, detail="Cannot connect to Ollama service. Please make sure the service is running.")
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        raise HTTPException(status_code=503, detail="Could not fetch available models")

@app.post("/process-youtube")
async def process_youtube(request: TranscriptionRequest, user: dict = Depends(get_current_user)):
    """Process YouTube video: tries to fetch existing transcript first, falls back to audio transcription"""
    if not request.youtube_url:
        raise HTTPException(status_code=400, detail="YouTube URL is required")

    logger.info(f"Processing YouTube URL: {request.youtube_url} for user: {user['id']}")
    audio_file = None
    video_title = "Unknown Title"
    transcription = None

    try:
        # Step 1: Try to get existing YouTube transcript (fast and free!)
        logger.info("Attempting to fetch existing YouTube transcript...")
        transcript_result = TranscriptFetcher.get_youtube_transcript(request.youtube_url)

        if transcript_result:
            transcription = transcript_result['transcript']
            logger.info(f"Successfully fetched transcript from {transcript_result['source']}")

            # Get video metadata for title
            try:
                ydl_opts = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(request.youtube_url, download=False)
                    video_title = info.get('title', 'Unknown Title')
            except Exception as e:
                logger.warning(f"Could not fetch video title: {str(e)}")
                video_title = "YouTube Video"

        # Step 2: Fall back to audio download + Whisper transcription
        if not transcription:
            logger.info("No transcript found, falling back to audio download and transcription...")
            download_result = download_youtube_audio(request.youtube_url)
            audio_file = download_result['audio_file']
            video_title = download_result['title']
            transcription = transcribe_audio(audio_file)
            logger.info("Audio transcription completed")

        # Save source to database FIRST to get source_id
        user_supabase = get_user_supabase_client(user['token'])
        source_result = user_supabase.table('sources').insert({
            "user_id": user['id'],
            "title": video_title,
            "url": request.youtube_url,
            "type": "youtube"
        }).execute()
        source_id = source_result.data[0]['id']
        logger.info(f"Saved source to database: {video_title} (ID: {source_id})")

        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'], user['token'])

        # Store transcript in vector database with source_id
        store_transcript_in_vector_db(transcription, source_id=source_id, source="youtube", url=request.youtube_url, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")

        # Get user's preferred model for summary generation
        try:
            preferences = UserPreferencesService.get_user_preferences(user['id'], user['token'])
            preferred_model = preferences.get('preferred_model', 'gemma3:1b')
        except Exception as e:
            logger.warning(f"Could not load user preferences for summary, using default: {str(e)}")
            preferred_model = 'gemma3:1b'

        # Generate summary using Ollama
        summary = generate_summary_ollama(transcription, preferred_model)

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

    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            logger.info(f"Saved temporary file: {temp_path}")

        # Transcribe audio
        transcription = transcribe_audio(temp_path)

        # Save source to database FIRST to get source_id
        user_supabase = get_user_supabase_client(user['token'])
        source_result = user_supabase.table('sources').insert({
            "user_id": user['id'],
            "title": file.filename,
            "url": file.filename,
            "type": "audio"
        }).execute()
        source_id = source_result.data[0]['id']
        logger.info(f"Saved source to database: {file.filename} (ID: {source_id})")

        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'], user['token'])

        # Store transcript in vector database with source_id
        store_transcript_in_vector_db(transcription, source_id=source_id, source="audio_upload", url=file.filename, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")

        # Get user's preferred model for summary generation
        try:
            preferences = UserPreferencesService.get_user_preferences(user['id'], user['token'])
            preferred_model = preferences.get('preferred_model', 'gemma3:1b')
        except Exception as e:
            logger.warning(f"Could not load user preferences for summary, using default: {str(e)}")
            preferred_model = 'gemma3:1b'

        # Generate summary using Ollama
        summary = generate_summary_ollama(transcription, preferred_model)
        return {
            "title": file.filename,
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
    """Process podcast: tries to fetch existing transcript first, falls back to audio transcription"""
    if not request.podcast_url:
        raise HTTPException(status_code=400, detail="Podcast URL is required")

    logger.info(f"Processing podcast URL: {request.podcast_url} for user: {user['id']}")
    fetcher = PodFetcher()
    file_path = None

    try:
        # PodFetcher already tries to get transcripts first (podscripts.co, RSS feeds, etc.)
        # then falls back to audio download if no transcript is available
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

        # Save source to database FIRST to get source_id
        user_supabase = get_user_supabase_client(user['token'])
        source_result = user_supabase.table('sources').insert({
            "user_id": user['id'],
            "title": full_title,
            "url": request.podcast_url,
            "type": "podcast"
        }).execute()
        source_id = source_result.data[0]['id']
        logger.info(f"Saved source to database: {full_title} (ID: {source_id})")

        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'], user['token'])

        # Store transcript in vector database with source_id
        store_transcript_in_vector_db(transcription, source_id=source_id, source="podcast", url=request.podcast_url, user_id=user['id'], vector_db=vector_db)
        logger.info("Transcript stored in vector database")

        # Get user's preferred model for summary generation
        try:
            preferences = UserPreferencesService.get_user_preferences(user['id'], user['token'])
            preferred_model = preferences.get('preferred_model', 'gemma3:1b')
        except Exception as e:
            logger.warning(f"Could not load user preferences for summary, using default: {str(e)}")
            preferred_model = 'gemma3:1b'

        # Generate summary
        summary = generate_summary_ollama(transcription, preferred_model)
        logger.info("Summary generated successfully")

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
        vector_db = get_user_vector_db(user['id'], user['token'])

        # Use user's preferred model if no specific model provided
        model_to_use = request.model
        if not model_to_use or model_to_use == "llama3.2:1b":  # Default fallback
            try:
                preferences = UserPreferencesService.get_user_preferences(user['id'], user['token'])
                model_to_use = preferences.get('preferred_model', 'gemma3:1b')
            except Exception as e:
                logger.warning(f"Could not load user preferences, using default: {str(e)}")
                model_to_use = 'gemma3:1b'

        chat_result = chat_with_ollama(request.message, vector_db, request.context, model_to_use)
        return chat_result  # Returns {"response": str, "sources": dict}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
async def search_transcripts(query: str, k: int = 5, user: dict = Depends(get_current_user)):
    """Search through stored transcripts using vector similarity"""
    try:
        # Get user-specific vector database
        vector_db = get_user_vector_db(user['id'], user['token'])

        results = vector_db.search(query, k=k)
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "content": doc['page_content'],
                "metadata": doc.get('metadata', {})
            })
        return {"results": formatted_results}
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sources")
async def get_sources(user: dict = Depends(get_current_user)):
    """Get all sources for the authenticated user with chunk counts"""
    try:
        user_supabase = get_user_supabase_client(user['token'])
        result = user_supabase.table('sources').select('*').eq('user_id', user['id']).order('created_at', desc=True).execute()

        # Get vector DB instance to check chunk counts
        vector_db = get_user_vector_db(user['id'], user['token'])

        # Format the response to match frontend expectations
        sources = []
        for item in result.data:
            # Get chunk count for this source
            chunk_count = vector_db.get_source_count(item['id'])

            sources.append({
                "id": item['id'],
                "title": item['title'],
                "url": item['url'],
                "type": item['type'],
                "addedAt": item['created_at'],
                "chunkCount": chunk_count
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
    """Delete a source and its associated vector data (CASCADE)"""
    try:
        # Use user's token for RLS
        user_supabase = get_user_supabase_client(user['token'])

        # First, verify the source belongs to the user
        result = user_supabase.table('sources').select('*').eq('id', source_id).eq('user_id', user['id']).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Source not found")

        # Delete from Supabase (CASCADE will automatically delete document_chunks)
        user_supabase.table('sources').delete().eq('id', source_id).eq('user_id', user['id']).execute()

        logger.info(f"Deleted source {source_id} and its chunks for user {user['id']}")

        return {"success": True, "message": "Source and associated chunks deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/preferences")
async def get_user_preferences(user: dict = Depends(get_current_user)):
    """Get the authenticated user's preferences"""
    try:
        preferences = UserPreferencesService.get_user_preferences(user['id'], user['token'])
        return preferences
    except Exception as e:
        logger.error(f"Error fetching user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/user/preferences")
async def update_user_preferences(preferences: PreferencesUpdate, user: dict = Depends(get_current_user)):
    """Update the authenticated user's preferences"""
    try:
        updated_preferences = UserPreferencesService.update_user_preferences(
            user['id'],
            user['token'],
            preferences.preferred_model
        )
        return updated_preferences
    except ValueError as e:
        # Invalid model name
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint that also verifies service connections"""
    status = {
        "status": "healthy",
        "whisper": "loaded",
        "ollama": "disconnected",
        "supabase": "disconnected"
    }

    try:
        # Check if Ollama service is running
        response = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=5)
        status["ollama"] = "connected" if response.status_code == 200 else "disconnected"
    except Exception as e:
        logger.warning(f"Ollama health check failed: {str(e)}")
        status["ollama"] = "disconnected"

    try:
        # Check if Supabase is accessible
        result = supabase.table('sources').select('id', count='exact').limit(1).execute()
        status["supabase"] = "connected"
    except Exception as e:
        logger.warning(f"Supabase health check failed: {str(e)}")

    return status

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)