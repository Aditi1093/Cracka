"""
utils/music.py
Music playback using pywhatkit (YouTube) or local files.
"""

import pywhatkit
import webbrowser
import urllib.parse
from core.logger import log_info, log_error


def play_song(command: str):
    """Play a song on YouTube from voice command."""
    song = command.lower()
    for word in ["play", "music", "song", "play song", "play music"]:
        song = song.replace(word, "")
    song = song.strip()

    if not song:
        return

    log_info(f"Playing: {song}")
    try:
        pywhatkit.playonyt(song)
    except Exception as e:
        log_error(f"pywhatkit error: {e}")
        # Fallback: open YouTube search
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(song)}"
        webbrowser.open(url)


def pause_music():
    """Pause/play media using keyboard shortcut."""
    import pyautogui
    pyautogui.press("playpause")


def next_track():
    import pyautogui
    pyautogui.press("nexttrack")


def prev_track():
    import pyautogui
    pyautogui.press("prevtrack")