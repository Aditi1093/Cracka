"""
╔══════════════════════════════════════════╗
║     CRACKA AI — COMMAND PROCESSOR        ║
║   brain/command_processor.py             ║
║   Extra routing layer — forwards all     ║
║   commands to core/ai_brain.py           ║
╚══════════════════════════════════════════╝

NOTE: Main command routing is done in core/ai_brain.py
This file exists as an extra layer for:
  - Pre-processing commands before routing
  - Post-processing responses after routing
  - Future: plugin system, command aliases
"""

from core.ai_brain import process
from core.logger import log_info, log_error


def handle_command(command: str, session=None) -> str:
    """
    Pre-process command, send to ai_brain, post-process response.

    Args:
        command: Raw voice command from Boss
        session: SessionMemory object (from main.py)

    Returns:
        Final response string
    """
    if not command or not command.strip():
        return ""

    command = _preprocess(command)

    try:
        response = process(command, session)
        response = _postprocess(response)
        log_info(f"[CommandProcessor] Handled: {command[:40]}")
        return response

    except Exception as e:
        log_error(f"[CommandProcessor] Error: {e}")
        return "Something went wrong Boss. Please try again."


def _preprocess(command: str) -> str:
    """
    Clean up command before sending to ai_brain.
    - Lowercase
    - Remove extra spaces
    - Fix common mic mishears
    """
    command = command.lower().strip()
    command = " ".join(command.split())  # Remove extra spaces

    # Fix common mic mishears
    fixes = {
        "crack a":   "cracka",
        "cracker":   "cracka",
        "open to":   "open",
        "close to":  "close",
        "you tube":  "youtube",
        "what sapp": "whatsapp",
        "face book": "facebook",
    }
    for wrong, correct in fixes.items():
        command = command.replace(wrong, correct)

    return command


def _postprocess(response: str) -> str:
    """
    Clean up response before speaking/displaying.
    - Remove extra whitespace
    - Truncate if too long for speech
    """
    if not response:
        return ""

    response = response.strip()

    # If response is very long, truncate for speech
    # (Full response still shown in GUI)
    if len(response) > 500:
        response = response[:500] + "..."

    return response


# ── Command aliases — Boss ke shortcut commands ───────────────────────────────
# Yeh commands automatically expand ho jaate hain
ALIASES = {
    "yt":        "open youtube",
    "gg":        "search google",
    "wa":        "open whatsapp",
    "ss":        "take screenshot",
    "vol up":    "volume up",
    "vol down":  "volume down",
    "calc":      "open calculator",
    "bye":       "goodbye",
}


def expand_alias(command: str) -> str:
    """Expand short aliases to full commands."""
    return ALIASES.get(command.lower().strip(), command)