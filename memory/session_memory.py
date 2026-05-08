"""
memory/session_memory.py
Current conversation ka short-term memory.
"""

from datetime import datetime


class SessionMemory:

    def __init__(self, max_turns: int = 15):
        self.history    = []
        self.max_turns  = max_turns
        self.session_start = datetime.now()

    def add_user_message(self, text: str):
        self.history.append({
            "role":    "user",
            "content": text,
            "time":    datetime.now().strftime("%H:%M:%S")
        })
        self._trim()

    def add_assistant_message(self, text: str):
        self.history.append({
            "role":    "assistant",
            "content": text,
            "time":    datetime.now().strftime("%H:%M:%S")
        })
        self._trim()

    def _trim(self):
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2):]

    def get_history(self) -> list:
        return self.history.copy()

    def get_history_as_text(self) -> str:
        lines = []
        for msg in self.history[-6:]:
            role = "Boss" if msg["role"] == "user" else "Cracka"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def clear(self):
        self.history = []

    def get_session_duration(self) -> str:
        delta = datetime.now() - self.session_start
        mins  = int(delta.total_seconds() // 60)
        return f"{mins} minutes"