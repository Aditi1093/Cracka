"""
╔══════════════════════════════════════════╗
║     CRACKA AI — MEMORY MANAGER           ║
║   memory/memory_manager.py               ║
║   Long-term memory, diary, mood tracker  ║
╚══════════════════════════════════════════╝

Stores:
  - Notes/facts Boss tells Cracka       → data/memory.json
  - Daily command diary                 → data/diary.json
  - Mood history                        → data/mood.json
"""

import json
import os
from datetime import datetime, date, timedelta
from collections import Counter

# ── File paths ────────────────────────────────────────────────────────────────
MEMORY_FILE = "data/memory.json"
DIARY_FILE  = "data/diary.json"
MOOD_FILE   = "data/mood.json"

os.makedirs("data", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load(path: str) -> dict:
    """Load a JSON file safely. Returns empty dict on error."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(path: str, data: dict):
    """Save data to a JSON file safely."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Memory] Save error: {e}")


def _today() -> str:
    return date.today().isoformat()  # e.g. "2026-06-09"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────────────────────
# CORE MEMORY — remember / recall / forget
# ─────────────────────────────────────────────────────────────────────────────

def remember(key: str, value: str):
    """Store a fact or note in memory."""
    data = _load(MEMORY_FILE)
    data[key] = {
        "value":     value,
        "timestamp": _now()
    }
    _save(MEMORY_FILE, data)


def recall(key: str) -> str:
    """Retrieve a specific fact from memory."""
    data = _load(MEMORY_FILE)
    if key in data:
        entry = data[key]
        return f"I remember Boss: {entry['value']} (saved on {entry['timestamp']})"
    return f"I don't remember anything about '{key}' Boss."


def recall_all() -> str:
    """Return all stored memories."""
    data = _load(MEMORY_FILE)
    if not data:
        return "Memory is empty Boss. Tell me something to remember!"
    lines = ["Here is what I remember Boss:"]
    for key, entry in data.items():
        lines.append(f"  [{key}]: {entry['value']}")
    return "\n".join(lines)


def smart_recall(command: str) -> str:
    """
    Search memory by keyword from a voice command.
    e.g. "what did i say about python" → searches for 'python' in memory
    """
    data = _load(MEMORY_FILE)
    if not data:
        return "Memory is empty Boss."

    # Extract keyword from command
    keyword = command.lower()
    for phrase in ["what did i say about", "what do i know about",
                   "what do you know about", "tell me about"]:
        keyword = keyword.replace(phrase, "").strip()

    if not keyword:
        return recall_all()

    # Search through all memory entries
    matches = []
    for key, entry in data.items():
        if keyword in key.lower() or keyword in entry["value"].lower():
            matches.append(f"  [{key}]: {entry['value']}")

    if matches:
        return f"Here is what I know about '{keyword}' Boss:\n" + "\n".join(matches)
    return f"I don't have any memory related to '{keyword}' Boss."


def forget(key: str) -> str:
    """Delete a specific memory entry."""
    data = _load(MEMORY_FILE)
    if key in data:
        del data[key]
        _save(MEMORY_FILE, data)
        return f"Forgot '{key}' Boss."
    return f"I don't have any memory called '{key}' Boss."


def clear_memory() -> str:
    """Clear ALL stored memories."""
    _save(MEMORY_FILE, {})
    return "All memories cleared Boss."


# ─────────────────────────────────────────────────────────────────────────────
# AUTO DETECT AND SAVE
# Called from main.py after every command — saves important info automatically
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that signal Boss is sharing personal info
_AUTO_SAVE_PATTERNS = {
    "my name is":      "boss_name",
    "i am":            "boss_identity",
    "i live in":       "boss_location",
    "i work at":       "boss_workplace",
    "i study at":      "boss_college",
    "my email is":     "boss_email",
    "my number is":    "boss_phone",
    "i like":          "boss_preference",
    "i love":          "boss_interest",
    "i hate":          "boss_dislike",
    "my birthday is":  "boss_birthday",
    "remind me":       "boss_reminder_hint",
}


def auto_detect_and_save(command: str):
    """
    Automatically detect and save personal info from commands.
    e.g. "my name is Aditi" → saves boss_name = "Aditi"
    Called silently from main.py — no response returned.
    """
    if not command:
        return

    cmd = command.lower().strip()

    for pattern, key in _AUTO_SAVE_PATTERNS.items():
        if pattern in cmd:
            # Extract the value after the pattern
            value = cmd.split(pattern, 1)[-1].strip()
            if value and len(value) > 1:
                remember(key, value)
            break


# ─────────────────────────────────────────────────────────────────────────────
# DIARY — log every command Boss gives
# ─────────────────────────────────────────────────────────────────────────────

def log_command_to_diary(command: str, response: str):
    """
    Save command + response to today's diary.
    Called from main.py after every successful command.
    """
    if not command:
        return

    diary = _load(DIARY_FILE)
    today = _today()

    if today not in diary:
        diary[today] = []

    diary[today].append({
        "time":     datetime.now().strftime("%H:%M:%S"),
        "command":  command,
        "response": response[:120] if response else ""  # Keep short
    })

    # Keep only last 30 days of diary
    keys = sorted(diary.keys())
    if len(keys) > 30:
        for old_key in keys[:-30]:
            del diary[old_key]

    _save(DIARY_FILE, diary)


def show_diary(day: str = None) -> str:
    """
    Show diary for a specific day.
    day = "2026-06-09" format, or None for today.
    """
    diary = _load(DIARY_FILE)

    if not diary:
        return "Diary is empty Boss. No commands logged yet."

    target = day or _today()

    if target not in diary:
        return f"No diary entries for {target} Boss."

    entries = diary[target]
    lines   = [f"Diary for {target} ({len(entries)} commands) Boss:"]

    for e in entries:
        lines.append(f"  [{e['time']}] You: {e['command']}")
        if e.get("response"):
            lines.append(f"           Cracka: {e['response'][:80]}")

    return "\n".join(lines)


def show_weekly_summary() -> str:
    """Show summary of commands used in the last 7 days."""
    diary = _load(DIARY_FILE)

    if not diary:
        return "No diary data yet Boss."

    # Get last 7 days
    week_commands = []
    for i in range(7):
        day = (date.today() - timedelta(days=i)).isoformat()
        if day in diary:
            for entry in diary[day]:
                week_commands.append(entry["command"])

    if not week_commands:
        return "No commands in the last 7 days Boss."

    total = len(week_commands)
    top   = Counter(week_commands).most_common(5)

    lines = [f"Weekly Summary Boss ({total} total commands):"]
    lines.append("Top commands this week:")
    for cmd, count in top:
        lines.append(f"  {count}x — {cmd}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# MOOD TRACKER
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that signal different moods in commands
_MOOD_KEYWORDS = {
    "happy":   ["happy", "great", "awesome", "excited", "love", "yay", "good", "amazing"],
    "sad":     ["sad", "upset", "unhappy", "depressed", "miss", "cry", "hate", "bad"],
    "angry":   ["angry", "annoyed", "frustrated", "irritated", "mad", "furious"],
    "tired":   ["tired", "sleepy", "exhausted", "bored", "dull"],
    "stressed":["stressed", "pressure", "deadline", "worried", "anxious", "nervous"],
    "neutral": [],
}


def _detect_mood_from_text(text: str) -> str:
    """Detect mood from command text using keyword matching."""
    text = text.lower()
    for mood, keywords in _MOOD_KEYWORDS.items():
        if any(word in text for word in keywords):
            return mood
    return "neutral"


def track_mood(command: str):
    """
    Detect and save Boss's mood from command text.
    Called silently from main.py after every command.
    """
    if not command:
        return

    mood  = _detect_mood_from_text(command)
    moods = _load(MOOD_FILE)
    today = _today()

    if today not in moods:
        moods[today] = []

    moods[today].append({
        "time":    datetime.now().strftime("%H:%M:%S"),
        "mood":    mood,
        "trigger": command[:60]
    })

    # Keep only last 30 days
    keys = sorted(moods.keys())
    if len(keys) > 30:
        for old_key in keys[:-30]:
            del moods[old_key]

    _save(MOOD_FILE, moods)


def get_mood_today() -> str:
    """Return mood summary for today."""
    moods = _load(MOOD_FILE)
    today = _today()

    if today not in moods or not moods[today]:
        return "No mood data for today yet Boss. Talk to me more!"

    entries       = moods[today]
    mood_counts   = Counter(e["mood"] for e in entries)
    dominant_mood = mood_counts.most_common(1)[0][0]
    total         = len(entries)

    lines = [f"Today's mood summary Boss ({total} readings):"]
    lines.append(f"  Dominant mood: {dominant_mood.upper()}")
    for mood, count in mood_counts.most_common():
        if mood != "neutral":
            lines.append(f"  {mood}: {count} time(s)")

    # Encouraging message
    mood_messages = {
        "happy":   "You had a great day Boss!",
        "sad":     "Hope tomorrow is better Boss. I am always here.",
        "angry":   "You seemed frustrated today Boss. Take rest.",
        "tired":   "You sounded tired today Boss. Sleep well!",
        "stressed":"You had a stressful day Boss. You handled it well!",
        "neutral": "A calm and steady day Boss!",
    }
    lines.append(mood_messages.get(dominant_mood, ""))

    return "\n".join(lines)


def get_mood_weekly() -> str:
    """Return mood summary for the last 7 days."""
    moods = _load(MOOD_FILE)

    if not moods:
        return "No mood data yet Boss."

    all_moods = []
    for i in range(7):
        day = (date.today() - timedelta(days=i)).isoformat()
        if day in moods:
            for entry in moods[day]:
                all_moods.append(entry["mood"])

    if not all_moods:
        return "No mood data in the last 7 days Boss."

    mood_counts   = Counter(all_moods)
    dominant_mood = mood_counts.most_common(1)[0][0]

    lines = [f"Weekly mood summary Boss ({len(all_moods)} readings):"]
    lines.append(f"  Overall mood: {dominant_mood.upper()}")
    for mood, count in mood_counts.most_common():
        pct = int(count / len(all_moods) * 100)
        lines.append(f"  {mood}: {count}x ({pct}%)")

    return "\n".join(lines)