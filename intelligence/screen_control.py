"""
intelligence/screen_control.py
Screen interaction: capture, click, find elements.
"""

import pyautogui
import os
from core.logger import log_error

pyautogui.FAILSAFE = True  # Move mouse to corner to stop


def capture_screen(path: str = "data/screen.png") -> str:
    """Take a screenshot and save it."""
    os.makedirs("data", exist_ok=True)
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(path)
        return f"Screenshot saved Boss at {path}"
    except Exception as e:
        log_error(f"Screenshot error: {e}")
        return "Could not take screenshot Boss."


def click_position(x: int, y: int) -> str:
    """Move to and click a screen position."""
    try:
        pyautogui.moveTo(x, y, duration=0.5)
        pyautogui.click()
        return f"Clicked at ({x}, {y}) Boss."
    except Exception as e:
        log_error(f"Click error: {e}")
        return "Click failed Boss."


def find_and_click(image_path: str) -> str:
    """Find an image on screen and click it."""
    try:
        location = pyautogui.locateCenterOnScreen(image_path, confidence=0.8)
        if location:
            pyautogui.click(location)
            return f"Found and clicked element Boss."
        else:
            return "Element not found on screen Boss."
    except Exception as e:
        log_error(f"Find click error: {e}")
        return "Could not find element Boss."


def get_screen_size() -> str:
    """Get screen resolution."""
    w, h = pyautogui.size()
    return f"Screen size: {w}x{h} Boss."