"""
automation/voice_typing.py
Voice dictation — types whatever Boss speaks.
"""

import pyautogui
from core.listener import listen
from core.voice_engine import speak
from core.logger import log_info


def start_dictation():
    """Start voice dictation mode. Say 'stop dictation' to exit."""
    speak("Dictation started Boss. Speak now. Say 'stop dictation' to stop.")
    log_info("Dictation mode started")

    while True:
        text = listen(timeout=10, phrase_limit=15)

        if not text:
            continue

        if "stop dictation" in text:
            speak("Stopping dictation Boss.")
            log_info("Dictation mode stopped")
            break

        # Correct common voice-to-text errors
        text = text.replace("full stop", ".")
        text = text.replace("comma", ",")
        text = text.replace("question mark", "?")
        text = text.replace("exclamation mark", "!")
        text = text.replace("new line", "\n")

        pyautogui.write(text + " ", interval=0.03)