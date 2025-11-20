"""
transcript_fetcher.py

Simple and efficient transcript extraction that prioritizes existing transcripts
over audio downloads and transcription.

Strategy:
1. Try to get existing transcripts (YouTube API, RSS feeds, etc.)
2. Only download audio and transcribe if no transcript exists
"""

import logging
import re
from typing import Optional, Dict
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)

logger = logging.getLogger(__name__)


class TranscriptFetcher:
    """Fetches transcripts from various sources, preferring existing text over audio transcription"""

    @staticmethod
    def extract_youtube_video_id(url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        """
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def get_youtube_transcript(url: str) -> Optional[Dict[str, str]]:
        """
        Try to fetch existing YouTube transcript/captions.

        Returns:
            Dict with 'transcript' and 'source' keys if successful, None otherwise
        """
        video_id = TranscriptFetcher.extract_youtube_video_id(url)
        if not video_id:
            logger.warning(f"Could not extract video ID from URL: {url}")
            return None

        try:
            logger.info(f"Attempting to fetch YouTube transcript for video ID: {video_id}")

            # Try to get transcript in English first, then any available language
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # Prefer manually created transcripts over auto-generated
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
                logger.info(f"Found manual English transcript for {video_id}")
                source = "youtube_manual_transcript"
            except:
                # Fall back to auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                    logger.info(f"Found auto-generated English transcript for {video_id}")
                    source = "youtube_auto_transcript"
                except:
                    # Try any available language
                    transcript = transcript_list.find_transcript(['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'ja', 'ko', 'zh-Hans', 'zh-Hant'])
                    logger.info(f"Found transcript in language: {transcript.language_code}")
                    source = f"youtube_transcript_{transcript.language_code}"

            # Fetch and format the transcript
            transcript_data = transcript.fetch()
            full_text = " ".join([entry['text'] for entry in transcript_data])

            logger.info(f"Successfully fetched YouTube transcript ({len(full_text)} characters)")
            return {
                'transcript': full_text,
                'source': source
            }

        except TranscriptsDisabled:
            logger.info(f"Transcripts are disabled for video {video_id}")
            return None
        except NoTranscriptFound:
            logger.info(f"No transcript found for video {video_id}")
            return None
        except VideoUnavailable:
            logger.warning(f"Video {video_id} is unavailable")
            return None
        except Exception as e:
            logger.error(f"Error fetching YouTube transcript: {str(e)}")
            return None

    @staticmethod
    def get_podcast_transcript(url: str, rss_data: Optional[Dict] = None) -> Optional[Dict[str, str]]:
        """
        Try to fetch existing podcast transcript from various sources.

        Args:
            url: Podcast episode URL
            rss_data: Optional RSS feed data that might contain transcript

        Returns:
            Dict with 'transcript' and 'source' keys if successful, None otherwise
        """
        # This is a placeholder for podcast transcript fetching
        # Can be extended to check:
        # - RSS feed <podcast:transcript> tags
        # - Episode description for transcript links
        # - Third-party transcript services (podscripts.co, etc.)

        logger.info(f"Podcast transcript fetching not yet implemented for: {url}")
        return None
