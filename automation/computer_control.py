"""
automation/computer_control.py
Keyboard, mouse, volume, screenshot control using PyAutoGUI.
"""

import pyautogui
import os
import time
from datetime import datetime
from core.logger import log_info, log_error

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1  # Small delay between actions


# ── KEYBOARD ─────────────────────────────────────────────────────────────────

def type_text(command: str):
    """Type text extracted from command."""
    # Remove trigger words
    for trigger in ["type", "write", "input"]:
        command = command.replace(trigger, "", 1)
    text = command.strip()
    if text:
        pyautogui.write(text, interval=0.04)
        log_info(f"Typed: {text}")


def press_enter():
    pyautogui.press("enter")


def press_key(key: str):
    """Press any keyboard key."""
    try:
        pyautogui.press(key)
    except Exception as e:
        log_error(f"Key press error: {e}")


def hotkey(*keys):
    """Press a keyboard shortcut."""
    pyautogui.hotkey(*keys)


def copy_text():
    pyautogui.hotkey("ctrl", "c")

def paste_text():
    pyautogui.hotkey("ctrl", "v")

def select_all():
    pyautogui.hotkey("ctrl", "a")

def undo():
    pyautogui.hotkey("ctrl", "z")


# ── MOUSE ─────────────────────────────────────────────────────────────────────

def move_mouse(x: int = 500, y: int = 500, duration: float = 0.8):
    pyautogui.moveTo(x, y, duration=duration)


def mouse_click(button: str = "left"):
    pyautogui.click(button=button)


def double_click():
    pyautogui.doubleClick()


def right_click():
    pyautogui.rightClick()


def scroll_down(amount: int = 500):
    pyautogui.scroll(-amount)


def scroll_up(amount: int = 500):
    pyautogui.scroll(amount)


def drag_mouse(x1, y1, x2, y2, duration=0.5):
    pyautogui.dragTo(x2, y2, duration=duration, button='left')


# ── VOLUME ────────────────────────────────────────────────────────────────────

def volume_up(times: int = 3):
    for _ in range(times):
        pyautogui.press("volumeup")

def volume_down(times: int = 3):
    for _ in range(times):
        pyautogui.press("volumedown")

def mute_volume():
    pyautogui.press("volumemute")


# ── SCREENSHOT ────────────────────────────────────────────────────────────────

def take_screenshot(path: str = None) -> str:
    """Take screenshot and save with timestamp."""
    os.makedirs("data/screenshots", exist_ok=True)
    if not path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"data/screenshots/screenshot_{ts}.png"
    image = pyautogui.screenshot()
    image.save(path)
    log_info(f"Screenshot saved: {path}")
    return path


# ── SYSTEM SHORTCUTS ──────────────────────────────────────────────────────────

def open_task_manager():
    pyautogui.hotkey("ctrl", "shift", "esc")


def show_desktop():
    pyautogui.hotkey("win", "d")


def lock_screen():
    pyautogui.hotkey("win", "l")


def open_run_dialog():
    pyautogui.hotkey("win", "r")


def switch_window():
    pyautogui.hotkey("alt", "tab")


def close_window():
    pyautogui.hotkey("alt", "f4")


def minimize_window():
    pyautogui.hotkey("win", "down")


def maximize_window():
    pyautogui.hotkey("win", "up")