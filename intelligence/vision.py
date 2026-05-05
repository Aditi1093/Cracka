"""
intelligence/vision.py
Screen capture and visual AI analysis using LLaVA (via Ollama).
"""

import os
import base64
import requests
from core.logger import log_error


def capture_screen(path: str = "data/screen.png") -> str:
    """Capture the current screen and save it."""
    try:
        import mss
        from PIL import Image
        os.makedirs("data", exist_ok=True)
        with mss.mss() as sct:
            screenshot = sct.grab(sct.monitors[1])
            img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            img.save(path)
        return path
    except Exception as e:
        # Fallback to pyautogui
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            return path
        except Exception as e2:
            log_error(f"Screen capture failed: {e2}")
            return ""


def describe_screen() -> str:
    """
    Capture screen and describe what's on it using LLaVA vision model.
    """
    path = capture_screen()
    if not path:
        return "Could not capture screen Boss."

    # Try Ollama LLaVA (local)
    try:
        import ollama
        response = ollama.chat(
            model="llava",
            messages=[{
                "role": "user",
                "content": "Describe what is visible on this screen. Be concise and helpful.",
                "images": [path]
            }]
        )
        return response["message"]["content"].strip()
    except Exception as e:
        log_error(f"[LLaVA] Error: {e}")

    # Fallback: just report capture success
    return f"Screen captured at {path} Boss. LLaVA model not available for description."


def read_text_from_screen() -> str:
    """Extract text from screen using OCR (pytesseract)."""
    path = capture_screen()
    if not path:
        return "Could not capture screen Boss."
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "No readable text found on screen Boss."
    except Exception as e:
        log_error(f"[OCR] Error: {e}")
        return "OCR not available. Please install pytesseract Boss."