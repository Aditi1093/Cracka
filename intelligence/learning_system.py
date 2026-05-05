"""
intelligence/learning_system.py
Tracks command usage patterns and learns from Boss's habits.
"""

import json
import os
from datetime import datetime
from collections import Counter

DATA_FILE = "data/cracka_learning.json"


def _load() -> dict:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        return {"commands": {}, "daily": {}, "total": 0}
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"commands": {}, "daily": {}, "total": 0}


def _save(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def learn_command(command: str):
    """Track usage of a command."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")

    # Overall frequency
    data["commands"][command] = data["commands"].get(command, 0) + 1
    data["total"] = data.get("total", 0) + 1

    # Daily tracking
    if today not in data["daily"]:
        data["daily"][today] = {}
    data["daily"][today][command] = data["daily"][today].get(command, 0) + 1

    _save(data)


def most_used(n: int = 1) -> str:
    """Return the most frequently used command(s)."""
    data = _load()
    if not data["commands"]:
        return None
    top = sorted(data["commands"].items(), key=lambda x: x[1], reverse=True)
    if n == 1:
        return top[0][0] if top else None
    return [cmd for cmd, _ in top[:n]]


def get_todays_commands() -> list:
    """Return today's used commands."""
    data = _load()
    today = datetime.now().strftime("%Y-%m-%d")
    return list(data.get("daily", {}).get(today, {}).keys())


def get_stats() -> str:
    """Return usage statistics summary."""
    data = _load()
    total = data.get("total", 0)
    unique = len(data["commands"])
    top = most_used()
    return f"Total commands: {total} | Unique: {unique} | Most used: {top}"