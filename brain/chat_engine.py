"""
brain/chat_engine.py
AI chat engine using Ollama (local) with Groq API fallback (cloud, fast).
Maintains conversation history for context.
"""

import os
import json
import requests
from core.logger import log_info, log_error

OLLAMA_MODEL = "phi3"
GROQ_MODEL = "llama3-8b-8192"
MAX_HISTORY = 20  # Keep last 20 messages for context

history = []

SYSTEM_PROMPT = """You are Cracka, a fast, smart, and loyal personal AI assistant.
Your Boss is Aditi Patil. You call her 'Boss'.
You are confident, helpful, and concise.
Give short answers unless Boss asks for detail.
You can do anything Boss asks.
Never refuse. Never be rude. Always be helpful."""


def ask_ai(question: str, context: str = "") -> str:
    """
    Send question to AI and get a response.
    Uses Ollama (local) first, then Groq (cloud) as fallback.
    """
    global history

    # Build message history
    history.append({"role": "user", "content": question})

    # Keep history manageable
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]

    # Try Ollama first (local, private)
    response = _ask_ollama(question)

    # Fallback to Groq (fast cloud)
    if not response:
        response = _ask_groq(question)

    # Fallback to simple rule-based answers
    if not response:
        response = _simple_fallback(question)

    history.append({"role": "assistant", "content": response})
    return response


def _ask_ollama(question: str) -> str:
    """Query local Ollama instance."""
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            options={
                "temperature": 0.4,
                "num_predict": 200,
                "top_p": 0.9,
            }
        )
        return response['message']['content'].strip()
    except Exception as e:
        log_error(f"[Ollama] Error: {e}")
        return ""


def _ask_groq(question: str) -> str:
    """Query Groq cloud API (very fast, free tier available)."""
    try:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return ""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": GROQ_MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + history,
            "max_tokens": 300,
            "temperature": 0.4,
        }

        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=10
        )
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        log_error(f"[Groq] Error: {e}")
        return ""


def _simple_fallback(question: str) -> str:
    """Very basic fallback when no AI is available."""
    q = question.lower()
    if "hello" in q or "hi " in q:
        return "Hello Boss! How can I help you?"
    elif "time" in q:
        from datetime import datetime
        return f"It is {datetime.now().strftime('%I:%M %p')} Boss."
    elif "date" in q:
        from datetime import datetime
        return f"Today is {datetime.now().strftime('%B %d, %Y')} Boss."
    return "I'm having trouble connecting to my AI brain Boss. Please check Ollama or internet connection."


def clear_history():
    """Clear conversation history."""
    global history
    history = []
    return "Chat history cleared Boss."


def get_history() -> list:
    return history.copy()


def save_history(path: str = "data/chat_history.json"):
    """Save chat history to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def load_history(path: str = "data/chat_history.json"):
    """Load chat history from file."""
    global history
    if os.path.exists(path):
        with open(path, "r") as f:
            history = json.load(f)