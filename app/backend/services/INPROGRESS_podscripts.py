#TODO: Integrate into our other services, clean up, add error handling, logging, etc.

import requests
from bs4 import BeautifulSoup
import urllib.parse

BASE_URL = "https://podscripts.co"

def get_podcast_url(podcast_name):
    """Search /podcasts for the given podcast name and return its URL."""
    url = f"{BASE_URL}/podcasts"
    resp = requests.get(url)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    pods = soup.find_all("div", class_="single-pod")

    for pod in pods:
        a = pod.find("a")
        if a and podcast_name.lower() in a.text.lower():
            return urllib.parse.urljoin(BASE_URL, a["href"])

    raise ValueError(f"Podcast '{podcast_name}' not found in directory.")


def get_episode_url(podcast_url, episode_title):
    """From a podcast page, find the episode link."""
    resp = requests.get(podcast_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    episodes = soup.find_all("a", href=True)
    for ep in episodes:
        if episode_title.lower() in ep.text.lower():
            return urllib.parse.urljoin(BASE_URL, ep["href"])

    raise ValueError(f"Episode '{episode_title}' not found.")


'''def get_transcript(episode_url):
    """Extract transcript text from the episode page."""
    resp = requests.get(episode_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    transcript_div = soup.find("div", class_="transcript")
    if not transcript_div:
        raise ValueError("Transcript not found on episode page.")

    return transcript_div.get_text(separator="\n", strip=True)
'''

def extract_transcript_from_episode(episode_url):
    """Extracts all transcript text from a Podscripts episode page."""
    resp = requests.get(episode_url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # All transcript sections
    sentence_divs = soup.find_all("div", class_="single-sentence")

    transcript_lines = []
    for div in sentence_divs:
        spans = div.find_all("span", class_="pod_text")
        for span in spans:
            text = span.get_text(strip=True)
            if text:
                transcript_lines.append(text)

    transcript = "\n".join(transcript_lines)
    return transcript


def fetch_transcript(podcast_name, episode_title):
    """End-to-end: get podcast → episode → transcript."""
    podcast_url = get_podcast_url(podcast_name)
    print(f"Found podcast: {podcast_url}")

    episode_url = get_episode_url(podcast_url, episode_title)
    print(f"Found episode: {episode_url}")

    transcript_text = extract_transcript_from_episode(episode_url)
    print("Transcript extracted successfully.")
    return transcript_text


# Example usage:
if __name__ == "__main__":
    podcast_name = "Huberman Lab"
    episode_title = "Essentials: Time Perception, Memory & Focus"
    try:
        transcript = fetch_transcript(podcast_name, episode_title)
        print(transcript)
    except Exception as e:
        print("Error:", e)
