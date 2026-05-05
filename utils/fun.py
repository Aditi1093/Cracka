"""
utils/fun.py
Fun features: jokes, motivational quotes.
"""

import requests
import random
from core.logger import log_error

FALLBACK_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem.",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "Why did the developer go broke? Because he used up all his cache!",
    "I told my computer I needed a break. Now it won't stop sending me vacation ads.",
]

FALLBACK_QUOTES = [
    "The secret of getting ahead is getting started. — Mark Twain",
    "Don't watch the clock; do what it does. Keep going. — Sam Levenson",
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. — Churchill",
    "Believe you can and you're halfway there. — Theodore Roosevelt",
]


def get_joke() -> str:
    """Fetch a random joke."""
    try:
        r = requests.get("https://official-joke-api.appspot.com/random_joke", timeout=5)
        data = r.json()
        return f"{data['setup']} ... {data['punchline']}"
    except Exception:
        return random.choice(FALLBACK_JOKES)


def get_quote() -> str:
    """Fetch a motivational quote."""
    try:
        r = requests.get("https://zenquotes.io/api/random", timeout=5)
        data = r.json()[0]
        return f"{data['q']} — {data['a']}"
    except Exception:
        return random.choice(FALLBACK_QUOTES)