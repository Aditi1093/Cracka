"""
utils/reminder_system.py
Voice-based reminder system with threading.
Say: "remind me in 5 minutes to drink water"
"""

import threading
import time
import re
import json
import os
from datetime import datetime, timedelta
from core.logger import log_info

REMINDERS_FILE = "data/reminders.json"
_active_reminders = []


def _save_reminders():
    os.makedirs("data", exist_ok=True)
    data = [{"message": r["message"], "due": r["due"].isoformat()} for r in _active_reminders]
    with open(REMINDERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def set_reminder(message: str, seconds: int) -> str:
    """Set a reminder for N seconds from now."""
    from core.voice_engine import speak

    due_time = datetime.now() + timedelta(seconds=seconds)
    reminder = {"message": message, "due": due_time, "seconds": seconds}
    _active_reminders.append(reminder)

    def _fire():
        time.sleep(seconds)
        speak(f"Boss! Reminder: {message}")
        print(f"\n⏰ REMINDER: {message}\n")
        if reminder in _active_reminders:
            _active_reminders.remove(reminder)

    t = threading.Thread(target=_fire, daemon=True)
    t.start()

    # Format time nicely
    if seconds < 60:
        time_str = f"{seconds} seconds"
    elif seconds < 3600:
        time_str = f"{seconds // 60} minute(s)"
    else:
        time_str = f"{seconds // 3600} hour(s)"

    log_info(f"Reminder set: '{message}' in {time_str}")
    return f"Reminder set Boss! I will remind you in {time_str}: {message}"


def parse_and_set_reminder(command: str) -> str:
    """
    Parse a voice command like:
    'remind me in 5 minutes to drink water'
    'set reminder after 2 hours to call mom'
    'remind me in 30 seconds to check oven'
    """
    command = command.lower()

    seconds = 0

    # Parse hours
    h_match = re.search(r"(\d+)\s*hour", command)
    if h_match:
        seconds += int(h_match.group(1)) * 3600

    # Parse minutes
    m_match = re.search(r"(\d+)\s*minute", command)
    if m_match:
        seconds += int(m_match.group(1)) * 60

    # Parse seconds
    s_match = re.search(r"(\d+)\s*second", command)
    if s_match:
        seconds += int(s_match.group(1))

    if seconds == 0:
        return "Please say how long Boss. Like 'remind me in 5 minutes to drink water'."

    # Extract the message (everything after 'to')
    msg_match = re.search(r"\bto\b(.+)$", command)
    if msg_match:
        message = msg_match.group(1).strip()
    else:
        # Remove time parts to get message
        msg = command
        for pattern in [r"\d+\s*hours?", r"\d+\s*minutes?", r"\d+\s*seconds?",
                        "remind me", "set reminder", "reminder", "in", "after"]:
            msg = re.sub(pattern, "", msg)
        message = msg.strip() or "your reminder"

    return set_reminder(message, seconds)


def list_reminders() -> str:
    """List all active reminders."""
    if not _active_reminders:
        return "No active reminders Boss."
    lines = ["Active reminders:"]
    for r in _active_reminders:
        due = r["due"].strftime("%H:%M:%S")
        lines.append(f"  • {r['message']} (at {due})")
    return "\n".join(lines)


def cancel_all_reminders() -> str:
    """Cancel all reminders."""
    _active_reminders.clear()
    return "All reminders cancelled Boss."