"""
╔══════════════════════════════════════════╗
║     CRACKA AI — SPOTIFY CONTROL          ║
║   utils/spotify_control.py               ║
║   Opens Spotify Web Player — no app      ║
║   installation or API setup needed!      ║
╚══════════════════════════════════════════╝
"""

import webbrowser
import urllib.parse
from core.logger import log_info, log_error


def play_spotify(command: str) -> str:
    """
    Open Spotify Web Player and search for a song.
    Example: 'play spotify shape of you'
    """
    if not command or not command.strip():
        return "Please tell me a song name Boss."

    song = command.lower()

    # Remove trigger words
    for word in ["play spotify", "spotify", "play", "song", "music"]:
        song = song.replace(word, "")
    song = song.strip()

    if not song:
        return "Please tell me which song to play on Spotify Boss."

    try:
        # Spotify Web Player search URL
        url = f"https://open.spotify.com/search/{urllib.parse.quote(song)}"
        webbrowser.open(url)
        log_info(f"[Spotify] Opened search for: {song}")
        return f"Opening Spotify and searching for '{song}' Boss."

    except Exception as e:
        log_error(f"[Spotify] Error: {e}")
        return "Could not open Spotify Boss. Please check your browser."


def open_spotify() -> str:
    """Open Spotify Web Player home page."""
    try:
        webbrowser.open("https://open.spotify.com")
        log_info("[Spotify] Opened web player")
        return "Opening Spotify Boss."
    except Exception as e:
        log_error(f"[Spotify] Error: {e}")
        return "Could not open Spotify Boss."