"""
╔══════════════════════════════════════════╗
║     CRACKA AI — CHAT ENGINE              ║
║   brain/chat_engine.py                   ║
║   AI chat using Ollama (local) +         ║
║   Groq API (cloud fallback)              ║
╚══════════════════════════════════════════╝

Priority:
  1. Ollama  — local, private, offline
  2. Groq    — cloud, fast, free tier
  3. Fallback — basic rule-based answers
"""

import os
import json
import requests
from core.logger import log_info, log_error

# ── Model config ──────────────────────────────────────────────────────────────
OLLAMA_MODEL  = "phi3"
GROQ_MODEL    = "llama3-8b-8192"
GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
MAX_HISTORY   = 20   # Last N messages kept for context

# ── Conversation history (in-memory) ─────────────────────────────────────────
_history: list = []

# ── System prompt — who Cracka is ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are Cracka, a fast, smart, and loyal personal AI assistant.
Your Boss is Aditi Patil. You always call her 'Boss'.
You are confident, helpful, and concise.
Give short answers unless Boss asks for detail.
You can help with anything Boss asks.
Never refuse. Never be rude. Always be helpful.
If you don't know something, say so honestly."""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def ask_ai(question: str, context: str = "") -> str:
    """
    Send question to AI and get a response.
    Tries Ollama first, then Groq, then simple fallback.

    Args:
        question: Boss's question or command
        context:  Optional session history as text (from SessionMemory)

    Returns:
        Response string
    """
    global _history

    if not question or not question.strip():
        return "Please say something Boss."

    # Add context to question if available
    full_question = question
    if context:
        full_question = f"[Conversation so far:\n{context}\n]\nBoss now says: {question}"

    # Add to history
    _history.append({"role": "user", "content": full_question})

    # Trim history to keep it manageable
    if len(_history) > MAX_HISTORY:
        _history = _history[-MAX_HISTORY:]

    # Try each AI in order
    response = _ask_ollama() or _ask_groq(question) or _simple_fallback(question)

    # Save response to history
    _history.append({"role": "assistant", "content": response})

    log_info(f"[ChatEngine] Q: {question[:50]}... A: {response[:50]}...")
    return response


# ─────────────────────────────────────────────────────────────────────────────
# AI BACKENDS
# ─────────────────────────────────────────────────────────────────────────────

def _ask_ollama() -> str:
    """
    Query local Ollama instance.
    Install: https://ollama.ai
    Run model: ollama run phi3
    """
    try:
        import ollama
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + _history,
            options={
                "temperature": 0.4,
                "num_predict": 250,
                "top_p":       0.9,
            }
        )
        result = response["message"]["content"].strip()
        if result:
            log_info("[ChatEngine] Ollama responded")
        return result

    except ImportError:
        # Ollama library not installed — skip silently
        return ""
    except Exception as e:
        log_error(f"[Ollama] Error: {e}")
        return ""


def _ask_groq(question: str) -> str:
    """
    Query Groq cloud API — very fast, free tier available.
    Get API key: https://console.groq.com
    Set env: GROQ_API_KEY=your_key_here
    """
    try:
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            return ""

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
        }

        payload = {
            "model":       GROQ_MODEL,
            "messages":    [{"role": "system", "content": SYSTEM_PROMPT}] + _history,
            "max_tokens":  300,
            "temperature": 0.4,
        }

        r = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=payload,
            timeout=10
        )
        r.raise_for_status()

        data   = r.json()
        result = data["choices"][0]["message"]["content"].strip()

        if result:
            log_info("[ChatEngine] Groq responded")
        return result

    except requests.exceptions.Timeout:
        log_error("[Groq] Request timed out")
        return ""
    except requests.exceptions.HTTPError as e:
        log_error(f"[Groq] HTTP error: {e}")
        return ""
    except Exception as e:
        log_error(f"[Groq] Error: {e}")
        return ""


def _simple_fallback(question: str) -> str:
    """
    Basic rule-based answers when no AI is available.
    Covers common questions so Cracka is never completely silent.
    """
    q = question.lower().strip()

    if any(x in q for x in ["hello", "hi ", "hey"]):
        return "Hello Boss! How can I help you?"

    elif "time" in q:
        from datetime import datetime
        return f"It is {datetime.now().strftime('%I:%M %p')} Boss."

    elif "date" in q:
        from datetime import datetime
        return f"Today is {datetime.now().strftime('%B %d, %Y')} Boss."

    elif "how are you" in q:
        return "I am running perfectly Boss! Always ready to help."

    elif "thank" in q:
        return "You are welcome Boss! Always here for you."

    elif "what is your name" in q:
        return "I am Cracka, your personal AI assistant Boss."

    elif "joke" in q:
        return "Why do programmers prefer dark mode? Because light attracts bugs! 😄"

    log_error("[ChatEngine] All AI backends failed — using fallback")
    return ("I am having trouble connecting to my AI brain Boss. "
            "Please check if Ollama is running, or set your GROQ_API_KEY.")


# ─────────────────────────────────────────────────────────────────────────────
# HISTORY MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

def clear_history() -> str:
    """Clear conversation history."""
    global _history
    _history = []
    log_info("[ChatEngine] History cleared")
    return "Chat history cleared Boss."


def get_history() -> list:
    """Return a copy of conversation history."""
    return _history.copy()


def save_history(path: str = "data/chat_history.json"):
    """Save conversation history to file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(_history, f, indent=2, ensure_ascii=False)
        log_info(f"[ChatEngine] History saved to {path}")
    except Exception as e:
        log_error(f"[ChatEngine] Save history error: {e}")


def load_history(path: str = "data/chat_history.json"):
    """Load conversation history from file."""
    global _history
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            _history = json.load(f)
        log_info(f"[ChatEngine] History loaded from {path}")
    except Exception as e:
        log_error(f"[ChatEngine] Load history error: {e}")
        _history = []


def get_history_summary() -> str:
    """Return a short summary of current conversation."""
    if not _history:
        return "No conversation history Boss."
    turns = len(_history) // 2
    return f"We have talked for {turns} turn(s) this session Boss."