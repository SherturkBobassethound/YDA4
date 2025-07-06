"""
pod_fetcher.py

Provides PodFetcher class for downloading podcast episodes
from Apple Podcasts URLs by:
  - Extracting episode titles
  - Converting to RSS feed URLs
  - Finding audio URLs via RSS
  - Downloading audio to a file

Designed for backend integration:
  - Returns file paths and metadata
  - Deletion and further processing are left to the caller
"""
#TODO: switch to logging from print statements

import os
import requests
import feedparser
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions


class PodFetcher:
    def __init__(self):
        """
        Initialize with target output directory and set up headless Chrome options.
        """
        self.output_dir = os.path.join(os.path.dirname(__file__), "..", "downloads")

        # Set up headless Chrome options for Selenium automation
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless") # No GUI
        self.chrome_options.add_argument("--no-sandbox") # Run without sandbox. Some environments like Docker require this
        self.chrome_options.add_argument("--disable-dev-shm-usage") # Avoid storing temporary files in /dev/shm (shared memory) which can cause crashes in some environments (Docker)

    def fetch(self, podcast_url: str) -> dict:
        """
        Main method to retrieve podcast metadata and download the MP3 file.

        Args:
            podcast_url (str): Apple Podcasts episode URL

        Returns:
            dict: {
                'podcast_name': str,  
                'episode_title': str,
                'rss_feed_url': str,
                'download_type': str,  # 'audio' or 'transcript'
                'download_url': str,
                'filepath': str
            }
        """
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

    def _get_episode_info(self, podcast_url: str) -> dict:
        """
        Collect episode title, RSS feed URL, and audio file URL.

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
        Scrape the Apple Podcasts page for the episode title using meta tags.

        Returns:
            str: episode title or None if not found
        """
        try:
            response = requests.get(podcast_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser') # Parse HTML with BeautifulSoup
            tag = soup.find('meta', property='og:title')  # Standard Open Graph title
            return tag['content'] if tag else None
        
        except requests.RequestException as e:
            print(f"[PodFetcher] Error fetching title: {e}")
            return None

    def _get_rss_feed_url(self, podcast_url: str) -> str:
        """
        Convert Apple Podcasts episode URL to its RSS feed URL
        using the rssfeedasap.com scraping service.

        Returns:
            str: RSS feed URL or None on failure
        """

        driver = webdriver.Chrome(options=self.chrome_options)
        wait = WebDriverWait(driver, timeout=10)  # timeout in seconds

        try:
            # Navigate to the RSS feed conversion site
            driver.get("https://rssfeedasap.com")

            # Wait for the input box to be present
            input_box = wait.until(expected_conditions.presence_of_element_located((By.NAME, "url")))
            input_box.clear()
            input_box.send_keys(podcast_url)

            # Wait for and click the "Get Feed" button
            button = wait.until(expected_conditions.element_to_be_clickable((By.XPATH, "//button[text()='Get Feed']")))
            button.click()

            # Wait for the resulting disabled input to appear
            feed_input = wait.until(expected_conditions.presence_of_element_located(
                (By.XPATH, "//input[@name='url' and @disabled]")
            ))

            return feed_input.get_attribute("value")

        except Exception as e:
            print(f"[PodFetcher] Error retrieving RSS feed: {e}")
            return None
        finally:
            driver.quit()
            

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
                if 'podcast_transcript' in entry:
                    return {'podcast_name': podcast_name, 'type': 'transcript', 'url': entry.podcast_transcript['url']}
                else:
                    for link in entry.enclosures:
                        if link.type.startswith("audio"):
                            return {'podcast_name': podcast_name, 'type': 'audio', 'url': link.href}
        return None
    


    def _download_file(self, url: str, title: str, filetype: str) -> str:
        """
        Download the file from a given URL and save it with a clean filename.

        Args:
            url (str): URL of the file
            title (str): Title of the episode to use for the filename
            filetype (str): Type of file to download ('transcript' or 'audio')

        Returns:
            str: Path to the downloaded MP3 file or None if failed
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
            return filepath
        except requests.RequestException as e:
            print(f"[PodFetcher] Error downloading {filetype}: {e}")
            return None



# Example usage for testing 
if __name__ == "__main__":
    fetcher = PodFetcher()
    podcast_url = "https://podcasts.apple.com/us/podcast/ama-ft-sholto-trenton-new-book-career-advice-given/id1516093381?i=1000700775714"
    info = fetcher.fetch(podcast_url)
    print(info)
