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

# ── PyQt5 MUST be created first, before any other import ─────────────────────
from PyQt5.QtWidgets import QApplication
app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)

# ── Core imports ──────────────────────────────────────────────────────────────
from core.voice_engine import speak
from core.listener    import listen
from core.ai_brain    import process
from core.wake_word   import listen_wake_word
from core.logger      import log_info, log_error
from gui              import CrackaGUI
from memory.session_memory import SessionMemory
from intelligence.learning_system import learn_command

# ── Optional memory helpers — safe fallback if not installed ──────────────────
try:
    from memory.memory_manager import (
        auto_detect_and_save,
        log_command_to_diary,
        track_mood,
    )
except ImportError:
    def auto_detect_and_save(cmd):      pass
    def log_command_to_diary(cmd, res): pass
    def track_mood(cmd):                pass

# ── Global state ──────────────────────────────────────────────────────────────
gui              = CrackaGUI()
session          = SessionMemory()

# FIX: this flag prevents wake_word_loop from starting a second assistant_loop
# while one is already running (was the double-loop bug in original code)
_assistant_running = threading.Event()

# ── Optional: connect network monitor to GUI ──────────────────────────────────
try:
    from security_scan.network_monitor import set_gui, auto_start_if_enabled
    set_gui(gui)
    auto_start_if_enabled()
    log_info("Network monitor connected to GUI")
except Exception as e:
    log_error(f"Network monitor setup skipped: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ASSISTANT LOOP
# Runs one full conversation session after wake word is detected.
# Exits when Boss says "stop", "exit", "goodbye", or "bye".
# ─────────────────────────────────────────────────────────────────────────────
def assistant_loop() -> None:
    """Main conversation loop — one session per wake word trigger."""
    greeting = "Hello Boss. I am Cracka, your personal AI assistant. How can I help you today?"
    speak(greeting)
    gui.add_message("Cracka", greeting)
    gui.set_status("Listening")

    while True:
        try:
            command = listen()

            # Empty result means mic timeout — keep waiting
            if not command:
                continue

            gui.add_message("You", command)
            gui.set_status("Thinking")
            log_info(f"Command received: {command}")

            # FIX: exit commands must be checked BEFORE calling process()
            # so they actually stop the loop instead of being sent to the AI
            if any(x in command for x in ("goodbye", "bye", "stop listening", "exit cracka")):
                response = "Goodbye Boss! Call me anytime."
                speak(response)
                gui.add_message("Cracka", response)
                gui.set_status("Idle — say wake word")
                log_info("Session ended by Boss.")
                break

            # Track command in memory
            session.add_user_message(command)
            learn_command(command)

            # Get response from brain
            response = process(command, session)

            # Log to memory
            auto_detect_and_save(command)
            track_mood(command)
            if response:
                log_command_to_diary(command, response)

            # Respond
            if response:
                session.add_assistant_message(response)
                gui.add_message("Cracka", response)
                speak(response)
                log_info(f"Response: {response}")

            gui.set_status("Listening")

        except KeyboardInterrupt:
            # Ctrl+C inside the loop — exit cleanly
            speak("Goodbye Boss!")
            gui.set_status("Stopped")
            break

        except Exception as e:
            # Any unexpected error — log it and keep going, don't crash
            log_error(f"Assistant loop error: {e}")
            gui.set_status("Error — Recovering")
            continue


# ─────────────────────────────────────────────────────────────────────────────
# WAKE WORD LOOP
# Runs forever in a background thread.
# When wake word is detected, starts assistant_loop() ONLY if one isn't running.
# ─────────────────────────────────────────────────────────────────────────────
def wake_word_loop() -> None:
    """Background thread — listens for wake word and triggers assistant."""
    log_info("Wake word listener started")

    while True:
        try:
            if listen_wake_word():
                # FIX: guard against double-trigger
                # If assistant is already running, ignore this wake word
                if _assistant_running.is_set():
                    log_info("Wake word detected but assistant already running — ignoring.")
                    continue

                _assistant_running.set()  # Mark as running
                gui.add_message("System", "Wake word detected!")
                speak("Yes Boss, I'm listening.")

                try:
                    assistant_loop()
                finally:
                    # Always clear the flag, even if assistant_loop crashes
                    _assistant_running.clear()

        except Exception as e:
            log_error(f"Wake word error: {e}")
            _assistant_running.clear()  # Safety: clear flag on error
            continue


# ─────────────────────────────────────────────────────────────────────────────
# START
# ─────────────────────────────────────────────────────────────────────────────
def start() -> None:
    """Entry point — starts all threads and the GUI."""
    log_info("Cracka AI v3.0 starting...")

    # Start wake word listener in background thread
    wake_thread = threading.Thread(target=wake_word_loop, daemon=True)
    wake_thread.start()

    # Show the GUI window
    gui.show()

    # FIX: gui.run() should NOT be called before app.exec_()
    # because app.exec_() IS the Qt event loop.
    # If your CrackaGUI.run() does something extra (like show splash),
    # call it before app.exec_(), otherwise remove it.
    # Check your gui.py — if run() just calls app.exec_(), remove the line below.
    # gui.run()   ← commented out to avoid double event loop

    try:
        exit_code = app.exec_()  # Blocks here until window is closed
    except KeyboardInterrupt:
        log_info("Keyboard interrupt received.")
        exit_code = 0
    finally:
        log_info("Cracka AI stopped.")

    sys.exit(exit_code)


if __name__ == "__main__":
    start()