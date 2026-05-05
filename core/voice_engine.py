"""
core/voice_engine.py
Text-to-Speech engine for Cracka AI.
Uses pyttsx3 (offline, fast) with gTTS fallback (online, natural).
"""

import pyttsx3
import threading
import os

# ── Windows mein pyttsx3 ek hi thread mein kaam karta hai ──────────────────
# isliye har speak() call ke liye naya engine banate hain thread mein

_speaking = False
_speak_lock = threading.Lock()


def speak(text: str, wait: bool = False):
    """
    Speak text using pyttsx3.
    Non-blocking by default (runs in background thread).
    wait=True karo agar next line speak khatam hone ke baad chalani ho.
    """
    print(f"\033[96mCracka:\033[0m {text}")

    def _do_speak():
        global _speaking
        with _speak_lock:
            _speaking = True
            try:
                # Windows par har thread mein naya engine banana padta hai
                eng = pyttsx3.init()
                eng.setProperty('rate', 160)
                eng.setProperty('volume', 1.0)

                # Best available voice set karo
                voices = eng.getProperty('voices')
                for v in voices:
                    vname = v.name.lower()
                    # Windows default voices: Zira (female), David (male)
                    if 'zira' in vname or 'david' in vname or 'heera' in vname:
                        eng.setProperty('voice', v.id)
                        break

                eng.say(text)
                eng.runAndWait()
                eng.stop()

            except Exception as e:
                print(f"[Voice] pyttsx3 error: {e}")
                # Fallback: Windows SAPI via os.system
                try:
                    safe = text.replace('"', '').replace("'", '')[:200]
                    os.system(
                        f'PowerShell -Command "Add-Type -AssemblyName System.Speech; '
                        f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                        f'$s.Rate = 1; $s.Speak(\\"{safe}\\")"'
                    )
                except Exception as e2:
                    print(f"[Voice] Fallback also failed: {e2}")
            finally:
                _speaking = False

    t = threading.Thread(target=_do_speak, daemon=True)
    t.start()

    if wait:
        t.join()


def speak_gtts(text: str):
    """
    Online TTS using gTTS — more natural voice, requires internet.
    pip install gtts playsound
    """
    try:
        from gtts import gTTS
        import pygame
        import tempfile

        tts = gTTS(text=text, lang='en', slow=False)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name
        tts.save(tmp)

        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        pygame.mixer.music.unload()
        os.remove(tmp)

    except ImportError:
        print("[gTTS] Install: pip install gtts pygame")
        speak(text, wait=True)
    except Exception as e:
        print(f"[gTTS] Error: {e}")
        speak(text, wait=True)


def set_voice_speed(rate: int = 160):
    os.environ['CRACKA_VOICE_RATE'] = str(rate)


def is_speaking() -> bool:
    return _speaking