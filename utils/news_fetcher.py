"""
utils/news_fetcher.py
Fetch latest news using NewsAPI.
Get free API key at: https://newsapi.org
Set NEWSAPI_KEY in environment.
"""

import os
import requests
from core.logger import log_error


def get_news(category: str = "technology", count: int = 5) -> str:
    """Fetch top headlines."""
    api_key = os.environ.get("NEWSAPI_KEY", "")

    if not api_key:
        # Fallback: Google News RSS (no key needed)
        return _get_news_rss(count)

    try:
        url = (f"https://newsapi.org/v2/top-headlines"
               f"?country=in&category={category}&pageSize={count}&apiKey={api_key}")
        r = requests.get(url, timeout=5)
        data = r.json()

        if data["status"] != "ok":
            return "Could not fetch news Boss."

        articles = data.get("articles", [])
        if not articles:
            return "No news articles found Boss."

        lines = [f"Top {len(articles)} news stories Boss:"]
        for i, a in enumerate(articles, 1):
            lines.append(f"  {i}. {a['title']}")

        return "\n".join(lines)

    except Exception as e:
        log_error(f"News fetch error: {e}")
        return _get_news_rss(count)


def _get_news_rss(count: int = 5) -> str:
    """Fallback: Fetch news from Google RSS."""
    try:
        import xml.etree.ElementTree as ET
        url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.content)
        items = root.findall(".//item")[:count]

        if not items:
            return "Could not fetch news Boss."

        lines = ["Latest news Boss:"]
        for i, item in enumerate(items, 1):
            title = item.findtext("title", "").split(" - ")[0]
            lines.append(f"  {i}. {title}")

        return "\n".join(lines)

    except Exception as e:
        log_error(f"RSS news error: {e}")
        return "News service unavailable Boss. Please check your internet connection."