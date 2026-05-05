"""
utils/internet.py
Internet utilities: search, fetch, check connectivity.
"""

import webbrowser
import urllib.parse
import requests
from core.logger import log_error


def search_google(command: str):
    """Search Google from a voice command."""
    query = command.lower()
    for word in ["search", "google", "look up", "find", "search for"]:
        query = query.replace(word, "")
    query = query.strip()
    if query:
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(url)


def search_youtube(command: str):
    """Search YouTube from a voice command."""
    query = command.lower()
    for word in ["search", "youtube", "search on youtube", "find on youtube"]:
        query = query.replace(word, "")
    query = query.strip()
    if query:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        webbrowser.open(url)


def open_url(url: str):
    """Open any URL in browser."""
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)


def check_internet() -> bool:
    """Check if internet is available."""
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False


def is_online() -> str:
    """Voice-friendly internet status check."""
    if check_internet():
        return "Internet connection is active Boss."
    return "No internet connection Boss. Please check your network."


def fetch_page_title(url: str) -> str:
    """Fetch the title of a webpage."""
    try:
        import re
        r = requests.get(url, timeout=5)
        match = re.search(r"<title>(.*?)</title>", r.text, re.IGNORECASE)
        return match.group(1).strip() if match else "No title found"
    except Exception as e:
        return f"Could not fetch page: {e}"