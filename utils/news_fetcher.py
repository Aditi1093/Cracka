"""
╔══════════════════════════════════════════════════════════════╗
║         CRACKA AI — NEWS FETCHER                             ║
║   utils/news_fetcher.py                                      ║
║   Fetch latest news via NewsAPI or Google RSS fallback.      ║
║   Get free API key: https://newsapi.org                      ║
║   Set NEWSAPI_KEY in environment or config.json.             ║
╚══════════════════════════════════════════════════════════════╝

HOW TO INTEGRATE IN ai_brain.py
────────────────────────────────
Step 1 — Replace the old news block:

    elif "news" in command:
        from utils.news_fetcher import get_news
        return get_news()

With:

    elif _is_news_command(command):
        from utils.news_fetcher import cracka_news_handler
        return cracka_news_handler(command)

Step 2 — Add this helper in the HELPERS section at bottom of ai_brain.py:

    def _is_news_command(command: str) -> bool:
        from utils.news_fetcher import NEWS_TRIGGERS
        return any(t in command for t in NEWS_TRIGGERS)
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from core.logger import log_error

# ─── Cache ────────────────────────────────────────────────────────────────────
_CACHE: dict = {}
_CACHE_TTL: int = 600       # 10 minutes — NewsAPI free plan: 100 req/day

# ─── Valid NewsAPI categories ─────────────────────────────────────────────────
_VALID_CATEGORIES = {
    "business", "entertainment", "general",
    "health", "science", "sports", "technology"
}

# ─── Trigger keywords for ai_brain.py routing ────────────────────────────────
NEWS_TRIGGERS = [
    # English
    "news", "headlines", "latest news", "top news", "breaking news",
    "what is happening", "what's happening", "current events",
    "sports news", "health news", "tech news", "business news",
    "science news", "entertainment news",
    # Hinglish
    "khabar", "khabarein", "kya chal raha hai", "aaj ki khabar",
    "news sunao", "news batao", "news dikhao",
    "sports ki khabar", "tech ki khabar",
]

# ─── Category alias map ───────────────────────────────────────────────────────
_CATEGORY_ALIASES: dict[str, str] = {
    # technology
    "technology": "technology", "tech": "technology",
    "technical":  "technology", "gadget": "technology",
    "gadgets":    "technology", "it": "technology",
    # sports
    "sports": "sports", "sport": "sports",
    "cricket": "sports", "football": "sports", "ipl": "sports",
    # health
    "health": "health", "medical": "health",
    "fitness": "health", "covid": "health",
    # business
    "business": "business", "finance": "business",
    "economy":  "business", "market": "business",
    "stock":    "business", "sensex": "business", "nifty": "business",
    # entertainment
    "entertainment": "entertainment", "bollywood": "entertainment",
    "movies": "entertainment", "film": "entertainment",
    "cinema": "entertainment",
    # science
    "science": "science", "space": "science",
    "isro": "science", "nasa": "science", "research": "science",
    # general
    "general": "general", "world": "general",
    "india": "general", "national": "general",
    "local": "general", "breaking": "general",
}

# ─── Number words (voice me digits words ban jaate hain) ──────────────────────
_NUMBER_WORDS: dict[str, int] = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5,
}


# ─── Public API ───────────────────────────────────────────────────────────────

def get_news(category: str = "technology", count: int = 5) -> str:
    """
    Core fetch function. Always validates inputs and uses cache.
    Safe to call directly from anywhere in Cracka.
    """
    count    = _clamp_count(count)
    category = _validate_category(category)

    cache_key = (category, count)
    cached = _CACHE.get(cache_key)
    if cached:
        ts, result = cached
        if time.time() - ts < _CACHE_TTL:
            return result

    api_key = os.environ.get("NEWSAPI_KEY", "").strip()
    result  = _fetch_newsapi(api_key, category, count) if api_key \
              else _fetch_rss(count)

    _CACHE[cache_key] = (time.time(), result)
    return result


def cracka_news_handler(command: str = "") -> str:
    """
    Smart voice command parser — called from ai_brain.py.

    Supported commands:
        "news"                      → technology, 5 headlines
        "sports news"               → sports, 5
        "health news 3"             → health, 3
        "give me 7 business news"   → business, 7
        "kya chal raha hai"         → general, 5
        "aaj ki khabar teen"        → general, 3
        "ipl news"                  → sports, 5
        "bollywood news paanch"     → entertainment, 5
        "sensex news do"            → business, 2
        "isro news"                 → science, 5
    """
    command  = command.lower().strip()
    category = _detect_category(command)
    count    = _detect_count(command)
    return get_news(category=category, count=count)


def clear_news_cache() -> None:
    """Flush cache manually. Call after setting NEWSAPI_KEY at runtime."""
    _CACHE.clear()


# ─── Private: Validation ──────────────────────────────────────────────────────

def _clamp_count(count: int) -> int:
    try:
        return max(1, min(int(count), 20))
    except (TypeError, ValueError):
        return 5


def _validate_category(category: str) -> str:
    c = category.lower().strip()
    return c if c in _VALID_CATEGORIES else "technology"


# ─── Private: Smart parsing ───────────────────────────────────────────────────

def _detect_category(command: str) -> str:
    """
    Scan command for any known alias.
    First match wins. Generic Hinglish triggers → 'general'.
    """
    for word, cat in _CATEGORY_ALIASES.items():
        if word in command:
            return cat

    hinglish_generic = ["khabar", "kya chal raha", "aaj ki", "sunao", "batao", "dikhao"]
    if any(h in command for h in hinglish_generic):
        return "general"

    return "technology"


def _detect_count(command: str) -> int:
    """
    Extract count from command.
    Handles digits ("3 news"), number words ("teen news"),
    and natural phrasing ("give me five headlines").
    """
    for word in command.split():
        if word.isdigit():
            return _clamp_count(int(word))
    for word in command.split():
        if word in _NUMBER_WORDS:
            return _clamp_count(_NUMBER_WORDS[word])
    return 5


# ─── Private: Fetch ───────────────────────────────────────────────────────────

def _fetch_newsapi(api_key: str, category: str, count: int) -> str:
    """Primary: NewsAPI.org"""
    try:
        url = (
            "https://newsapi.org/v2/top-headlines"
            f"?country=in&category={category}"
            f"&pageSize={count}&apiKey={api_key}"
        )
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()

        if data.get("status") != "ok":
            log_error(f"NewsAPI error: {data.get('message', 'unknown')}")
            return _fetch_rss(count)

        articles = [
            a for a in data.get("articles", [])
            if a.get("title") and a["title"] != "[Removed]"
        ]

        if not articles:
            return f"No {category} news found right now Boss."

        label = category.capitalize()
        lines = [f"Top {len(articles)} {label} news Boss:"]
        for i, a in enumerate(articles, 1):
            lines.append(f"  {i}. {a['title'].strip()}")
        return "\n".join(lines)

    except requests.Timeout:
        log_error("NewsAPI timeout — falling back to RSS")
        return _fetch_rss(count)
    except requests.HTTPError as e:
        log_error(f"NewsAPI HTTP error: {e}")
        return _fetch_rss(count)
    except requests.RequestException as e:
        log_error(f"NewsAPI request failed: {e}")
        return _fetch_rss(count)
    except Exception as e:
        log_error(f"NewsAPI unexpected error: {e}")
        return _fetch_rss(count)


def _fetch_rss(count: int) -> str:
    """Fallback: Google News RSS — no API key needed."""
    count = _clamp_count(count)
    try:
        url  = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
        r    = requests.get(url, timeout=5)
        r.raise_for_status()
        root  = ET.fromstring(r.content)
        items = root.findall(".//item")[:count]

        if not items:
            return "Could not fetch news Boss. Check your internet connection."

        lines = ["Latest news Boss:"]
        for i, item in enumerate(items, 1):
            raw   = item.findtext("title", "").strip()
            # rsplit removes only trailing " - Source Name" safely
            title = raw.rsplit(" - ", 1)[0].strip() if " - " in raw else raw
            if title:
                lines.append(f"  {i}. {title}")
        return "\n".join(lines)

    except requests.Timeout:
        log_error("RSS timeout")
        return "News service timed out Boss. Check your internet."
    except ET.ParseError as e:
        log_error(f"RSS parse error: {e}")
        return "News feed format changed Boss. Will fix soon."
    except requests.RequestException as e:
        log_error(f"RSS request error: {e}")
        return "Could not reach news service Boss."
    except Exception as e:
        log_error(f"RSS unexpected error: {e}")
        return "News service unavailable Boss."