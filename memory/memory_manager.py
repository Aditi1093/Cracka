"""
memory/memory_manager.py
Persistent key-value memory for Cracka AI.
Stores notes, preferences, facts Boss tells Cracka.
"""

import json
import os
from datetime import datetime

MEMORY_FILE = "data/memory.json"


def _load() -> dict:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def remember(key: str, value: str):
    """Store a fact in memory."""
    data = _load()
    data[key] = {
        "value": value,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    _save(data)


def recall(key: str) -> str:
    """Retrieve a fact from memory."""
    data = _load()
    if key in data:
        entry = data[key]
        return f"Boss told me: {entry['value']} (on {entry['timestamp']})"
    return "I don't remember that Boss. Maybe you haven't told me yet."


def recall_all() -> str:
    """Return all stored memories."""
    data = _load()
    if not data:
        return "Memory is empty Boss."
    lines = ["Here's what I remember Boss:"]
    for key, entry in data.items():
        lines.append(f"  [{key}]: {entry['value']}")
    return "\n".join(lines)


def forget(key: str) -> str:
    """Delete a specific memory."""
    data = _load()
    if key in data:
        del data[key]
        _save(data)
        return f"Forgot '{key}' Boss."
    return f"I don't have any memory called '{key}' Boss."


def clear_memory():
    """Clear all memories."""
    _save({})
    return "All memories cleared Boss."