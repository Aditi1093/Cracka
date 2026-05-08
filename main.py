"""
╔══════════════════════════════════════════╗
║         CRACKA AI - MAIN ENTRY           ║
║     Personal AI Assistant v3.0           ║
╚══════════════════════════════════════════╝
Run: python main.py
"""

import threading
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── PyQt5 SABSE PEHLE ────────────────────────────────────────────────────────
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

# ── Baaki imports ─────────────────────────────────────────────────────────────
from core.voice_engine import speak
from core.listener import listen
from core.ai_brain import process
from core.wake_word import listen_wake_word
from core.logger import log_info, log_error
from gui import CrackaGUI
from memory.session_memory import SessionMemory
from intelligence.learning_system import learn_command

# Memory — safe fallback
try:
    from memory.memory_manager import (
        auto_detect_and_save,
        log_command_to_diary,
        track_mood
    )
except ImportError:
    def auto_detect_and_save(cmd): pass
    def log_command_to_diary(cmd, res): pass
    def track_mood(cmd): pass

# ── Global objects ────────────────────────────────────────────────────────────
gui     = CrackaGUI()
session = SessionMemory()

# ── FIX 1: Network monitor ko GUI se connect karo ────────────────────────────
try:
    from security_scan.network_monitor import set_gui, auto_start_if_enabled
    set_gui(gui)                  # GUI popup alerts ke liye
    auto_start_if_enabled()       # config mein ON hai toh auto-start
    log_info("Network monitor connected to GUI")
except Exception as e:
    log_error(f"Network monitor setup error: {e}")


# ── Assistant main loop ───────────────────────────────────────────────────────
def assistant_loop():
    greeting = "Hello Boss. I am Cracka, your personal AI assistant. How can I help you today?"
    speak(greeting)
    gui.add_message("Cracka", greeting)
    gui.set_status("Listening")

    while True:
        try:
            command = listen()

            if not command:
                continue

            gui.add_message("You", command)
            gui.set_status("Thinking")
            log_info(f"Command received: {command}")

            session.add_user_message(command)
            learn_command(command)

            response = process(command, session)

            # Memory tracking
            auto_detect_and_save(command)
            track_mood(command)
            if response:
                log_command_to_diary(command, response)

            if response:
                session.add_assistant_message(response)
                gui.add_message("Cracka", response)
                speak(response)
                log_info(f"Response: {response}")

            gui.set_status("Listening")

        except KeyboardInterrupt:
            speak("Goodbye Boss!")
            break
        except Exception as e:
            log_error(f"Assistant loop error: {e}")
            gui.set_status("Error - Recovering")
            continue


# ── Wake word listener ────────────────────────────────────────────────────────
def wake_word_loop():
    log_info("Wake word listener started")
    while True:
        try:
            if listen_wake_word():
                gui.add_message("System", "Wake word detected!")
                speak("Yes Boss, I'm listening.")
                assistant_loop()
        except Exception as e:
            log_error(f"Wake word error: {e}")
            continue


# ── Start ─────────────────────────────────────────────────────────────────────
def start():
    log_info("Cracka AI v3.0 starting...")

    t = threading.Thread(target=wake_word_loop, daemon=True)
    t.start()

    gui.show()
    gui.run()

    try:
        exit_code = app.exec_()
    except KeyboardInterrupt:
        exit_code = 0
    finally:
        log_info("Cracka AI stopped.")
    sys.exit(exit_code)


if __name__ == "__main__":
    start()