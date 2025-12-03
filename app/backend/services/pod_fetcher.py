"""
pod_fetcher.py

Provides PodFetcher class for downloading podcast episodes
from Apple Podcasts URLs by:
  - First, attempting to scrape a transcript from podscripts.co
  - If transcript scraping fails, falling back to:
    - Extracting episode titles
    - Converting to RSS feed URLs
    - Finding transcript or audio URLs via RSS
    - Downloading audio/transcript to a file

Designed for backend integration:
  - Returns file paths and metadata
  - Deletion and further processing are left to the caller
"""
#TODO: switch to logging from print statements

import os
import requests
import feedparser
import json
import urllib.parse
from pathlib import Path
from bs4 import BeautifulSoup


class PodFetcher:
    
    # Base URL for the new transcript scraping service
    _PODSCRIPTS_BASE_URL = "https://podscripts.co"

    def __init__(self):
        """
        Initialize with target output directory.
        """
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "downloads")
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)


    def fetch(self, podcast_url: str) -> dict:
        """
        Main method to retrieve podcast metadata and download the MP3 file.
        
        Tries to scrape transcript from podscripts.co first.
        If that fails, falls back to the RSS feed method.

        Args:
            podcast_url (str): Apple Podcasts episode URL

        Returns:
            dict: {
                'podcast_name': str,  
                'episode_title': str,
                'rss_feed_url': str or None,
                'download_type': str,  # 'audio' or 'transcript'
                'download_url': str,
                'filepath': str
            }
        """
        
        # --- NEW: Try scraping from podscripts.co first ---
        print(f"[PodFetcher] Attempting to scrape transcript from podscripts.co for: {podcast_url}")
        try:
            podcast_name, episode_title, transcript_text = self._podscripts_fetch_transcript(podcast_url)
            
            if transcript_text:
                filepath = self._save_transcript_string(transcript_text, episode_title)
                if filepath:
                    print("[PodFetcher] Successfully scraped transcript from podscripts.co")
                    return {
                        'podcast_name': podcast_name,
                        'episode_title': episode_title,
                        'rss_feed_url': None, # We skipped RSS
                        'download_type': 'transcript',
                        'download_url': 'scraped:podscripts.co', # Placeholder
                        'filepath': filepath
                    }
        except Exception as e:
            print(f"[PodFetcher] podscripts.co scrape failed: {e}. Falling back to RSS method.")
        # --- End of new logic ---


        # --- FALLBACK: Original RSS feed logic ---
        print("[PodFetcher] Using original RSS feed method.")
        # Gather all necessary info from the URL
        info = self._get_episode_info(podcast_url)
        if not info:
            raise ValueError("Could not retrieve episode information.")

        # Download the MP3 or transcript file using extracted URL and title
        filepath = self._download_file(info["download_url"], info["episode_title"], info["download_type"])
        if not filepath:
            raise ValueError(f"{info['download_type']} download failed.")

        info["filepath"] = filepath
        return info

    # --- New methods for podscripts.co scraping ---

    def _podscripts_extract_info_from_apple_url(self, apple_podcast_url):
        """
        Extracts podcast and episode title from the Apple Podcasts page
        using the JSON-LD schema.
        """
        resp = requests.get(apple_podcast_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        
        schema_script = soup.find("script", {"id": "schema:episode", "type": "application/ld+json"})
        
        if schema_script:
            data = json.loads(schema_script.string)
            
            podcast_title = data.get("partOfSeries", {}).get("name")
            episode_name = data.get("name")
            
            return podcast_title, episode_name
        else:
            # Fallback to just getting episode title if schema fails
            # This will likely cause podscripts lookup to fail, which is fine (it will trigger RSS)
            print("[PodFetcher] Warning: Could not find JSON-LD schema. Trying og:title fallback.")
            episode_title = self._get_episode_title_fallback(soup)
            return None, episode_title

    def _podscripts_get_podcast_url(self, podcast_name):
        """Search /podcasts on podscripts.co for the given podcast name and return its URL."""
        url = f"{self._PODSCRIPTS_BASE_URL}/podcasts"
        resp = requests.get(url)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        pods = soup.find_all("div", class_="single-pod") # This is the key to finding the podcasts available

        for pod in pods:
            a = pod.find("a")
            if a and podcast_name.lower() in a.text.lower():
                return urllib.parse.urljoin(self._PODSCRIPTS_BASE_URL, a["href"])

        raise ValueError(f"Podcast '{podcast_name}' not found in podscripts.co directory.")


    def _podscripts_get_episode_url(self, podcast_url, episode_title):
        """From a podscripts.co podcast page, find the episode link."""
        resp = requests.get(podcast_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        episodes = soup.find_all("a", href=True)
        for ep in episodes:
            # Simple substring match
            if episode_title.lower() in ep.text.lower():
                return urllib.parse.urljoin(self._PODSCRIPTS_BASE_URL, ep["href"])

        raise ValueError(f"Episode '{episode_title}' not found on podscripts.co.")

    def _podscripts_extract_transcript(self, episode_url):
        """Extracts all transcript text from a Podscripts episode page."""
        resp = requests.get(episode_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # All transcript sections
        sentence_divs = soup.find_all("div", class_="single-sentence")
        if not sentence_divs:
            raise ValueError("Transcript not found on episode page (no 'single-sentence' divs).")

        transcript_lines = []
        for div in sentence_divs:
            spans = div.find_all("span", class_="pod_text")
            for span in spans:
                text = span.get_text(strip=True)
                if text:
                    transcript_lines.append(text)

        transcript = "\n".join(transcript_lines)
        if not transcript:
            raise ValueError("Transcript text was empty.")
        return transcript


    def _podscripts_fetch_transcript(self, apple_podcast_url):
        """End-to-end: get podcast → episode → transcript from podscripts.co."""

        podcast_name, episode_title = self._podscripts_extract_info_from_apple_url(apple_podcast_url)
        if not podcast_name or not episode_title:
            raise ValueError(f"Could not extract podcast/episode name from Apple URL: {apple_podcast_url}")

        podcast_url = self._podscripts_get_podcast_url(podcast_name)
        print(f"[PodFetcher] podscripts.co: Found podcast: {podcast_url}")

        episode_url = self._podscripts_get_episode_url(podcast_url, episode_title)
        print(f"[PodFetcher] podscripts.co: Found episode: {episode_url}")

        transcript_text = self._podscripts_extract_transcript(episode_url)
        print("[PodFetcher] podscripts.co: Transcript extracted successfully.")
        return podcast_name, episode_title, transcript_text

    def _save_transcript_string(self, transcript_text: str, title: str) -> str:
        """
        Saves a transcript string to a .txt file.

        Args:
            transcript_text (str): The transcript content.
            title (str): Title of the episode to use for the filename

        Returns:
            str: Path to the downloaded .txt file or None if failed
        """
        ext = ".txt"
        # Clean the filename to avoid OS issues caused by special characters
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}{ext}"
        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(transcript_text)
            return filepath
        except Exception as e:
            print(f"[PodFetcher] Error saving transcript string: {e}")
            return None


    # --- Original RSS Fallback Methods ---

    def _get_episode_info(self, podcast_url: str) -> dict:
        """
        Collect episode title, RSS feed URL, and audio file URL.
        (Original fallback method)

        Returns:
            dict with keys: episode_title, rss_feed_url, audio_file_url
        """
        title = self._get_episode_title(podcast_url)
        if not title:
            return None

        rss_url = self._get_rss_feed_url(podcast_url)
        if not rss_url:
            return None

        download_info = self._get_download_url_from_rss(rss_url, title)
        if not download_info:
            return None

        return {
            "podcast_name": download_info["podcast_name"],
            "episode_title": title,
            "rss_feed_url": rss_url,
            "download_type": download_info["type"],
            "download_url": download_info["url"]
        }


    def _get_episode_title(self, podcast_url: str) -> str:
        """
        Scrape the Apple Podcasts page for the episode title.
        Tries JSON-LD schema first, then falls back to meta tags.
        """
        try:
            response = requests.get(podcast_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser') # Parse HTML with BeautifulSoup
            
            # Try JSON-LD schema first
            schema_script = soup.find("script", {"id": "schema:episode", "type": "application/ld+json"})
            if schema_script:
                data = json.loads(schema_script.string)
                if data and "name" in data:
                    return data["name"]
            
            print("[PodFetcher] JSON-LD schema not found for title, falling back to og:title")
            # Fallback to Open Graph
            return self._get_episode_title_fallback(soup)
        
        except requests.RequestException as e:
            print(f"[PodFetcher] Error fetching title: {e}")
            return None

    def _get_episode_title_fallback(self, soup: BeautifulSoup) -> str:
        """Helper to get title from og:title meta tag"""
        tag = soup.find('meta', property='og:title')  # Standard Open Graph title
        if tag:
            return tag['content']
        
        print("[PodFetcher] Error: Could not find episode title from any source.")
        return None

    def _get_rss_feed_url(self, podcast_url: str) -> str:
        """
        Convert Apple Podcasts episode URL to its RSS feed URL
        using the rssfeedasap.com scraping service.

        Returns:
            str: RSS feed URL or None on failure
        """
        # Use direct API method (Selenium removed)
        return self._get_rss_feed_url_fallback(podcast_url)

    def _get_rss_feed_url_fallback(self, podcast_url: str) -> str:
        """
        Get RSS feed URL using direct API calls (extracts podcast ID from Apple Podcasts URL)
        """
        try:
            # Try to extract podcast ID from Apple Podcasts URL
            if "podcasts.apple.com" in podcast_url:
                # Extract podcast ID from URL
                import re
                match = re.search(r'/podcast/[^/]+/id(\d+)', podcast_url)
                if match:
                    podcast_id = match.group(1)
                    # Try to construct RSS URL directly
                    rss_url = f"https://feeds.simplecast.com/{podcast_id}"
                    
                    # Test if the RSS feed is valid
                    response = requests.get(rss_url, timeout=10)
                    if response.status_code == 200:
                        return rss_url
                    
                    # Try alternative RSS URL format
                    rss_url = f"https://feeds.megaphone.fm/{podcast_id}"
                    response = requests.get(rss_url, timeout=10)
                    if response.status_code == 200:
                        return rss_url
            
            print("[PodFetcher] Fallback method could not find RSS feed")
            return None
            
        except Exception as e:
            print(f"[PodFetcher] Fallback method error: {e}")
            return None
    


    def _get_download_url_from_rss(self, rss_url: str, episode_title: str) -> dict:
        """
        Parse the RSS feed to find the MP3 URL that matches the episode title.

        Args:
            rss_url (str): RSS feed URL
            episode_title (str): Title to match in feed entries

        Returns:
            dict: {'type': 'transcript' or 'audio', 'url': str} or None if not found
        """

        feed = feedparser.parse(rss_url)
        podcast_name = feed.feed.get('title', 'Unknown Podcast')

        # Iterate through feed entries to find the matching episode based on the title scraped from Apple Podcasts
        for entry in feed.entries:
            if episode_title.lower() in entry.title.lower():
                # Priority 1: Check for a transcript link
                if 'podcast_transcript' in entry:
                    return {'podcast_name': podcast_name, 'type': 'transcript', 'url': entry.podcast_transcript['url']}
                
                # Priority 2: Check for an audio enclosure
                for link in entry.enclosures:
                    if link.type.startswith("audio"):
                        return {'podcast_name': podcast_name, 'type': 'audio', 'url': link.href}
        
        print(f"[PodFetcher] Could not find episode '{episode_title}' in RSS feed.")
        return None
    


    def _download_file(self, url: str, title: str, filetype: str) -> str:
        """
        Download the file from a given URL and save it with a clean filename.

        Args:
            url (str): URL of the file
            title (str): Title of the episode to use for the filename
            filetype (str): Type of file to download ('transcript' or 'audio')

        Returns:
            str: Path to the downloaded file or None if failed
        """

        ext = ".txt" if filetype == "transcript" else ".mp3"
        # Clean the filename to avoid OS issues caused by special characters
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_title}{ext}"
        filepath = os.path.join(self.output_dir, filename)

        # Download the file and save it to the specified path (downloads directory)
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"[PodFetcher] Successfully downloaded {filetype} to {filepath}")
            return filepath
        except requests.RequestException as e:
            print(f"[PodFetcher] Error downloading {filetype}: {e}")
            return None



# Example usage for testing 
if __name__ == "__main__":
    fetcher = PodFetcher()
    
    # --- Test 1: URL with a known transcript on podscripts.co ---
    print("\n--- TEST 1: Huberman Lab (should scrape from podscripts.co) ---")
    url_with_transcript = "https://podcasts.apple.com/us/podcast/huberman-lab/id1545953110?i=1000727833630"
    try:
        info_scrape = fetcher.fetch(url_with_transcript)
        print("Fetch successful. Info:")
        print(json.dumps(info_scrape, indent=2))
    except Exception as e:
        print(f"Fetch failed: {e}")

    # --- Test 2: URL without a transcript on podscripts.co (should use RSS) ---
    print("\n--- TEST 2: Random Podcast (should fall back to RSS) ---")
    url_rss_fallback = "https://podcasts.apple.com/us/podcast/ama-ft-sholto-trenton-new-book-career-advice-given/id1516093381?i=1000700775714"
    try:
        info_rss = fetcher.fetch(url_rss_fallback)
        print("Fetch successful. Info:")
        print(json.dumps(info_rss, indent=2))
    except Exception as e:
        print(f"Fetch failed: {e}")
