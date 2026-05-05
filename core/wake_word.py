"""
core/wake_word.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cracka AI — Wake Word Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vosk se exact "Cracka" detect karta hai.
No internet, no account, bilkul free!

Model download karo:
  https://alphacephei.com/vosk/models
  → vosk-model-small-en-us-0.15.zip
  → Extract karo: CrackaAI/models/vosk-model-small-en-us/
"""

import os
import json
import queue
import threading

# ── Wake words ────────────────────────────────────────────────────────────────
WAKE_WORDS = [
    "cracka",
    "crack a",
    "kraka",
    "jarvis",
    "hey jarvis",
    "mj",
    "baby",
]

# Vosk model path
VOSK_MODEL_PATH = "models/vosk-model-small-en-us"


def listen_wake_word() -> bool:
    """
    Vosk se exact 'Cracka' detect karo.
    Fallback: Google STT agar Vosk model nahi hai.
    """
    # Vosk model available hai?
    if os.path.exists(VOSK_MODEL_PATH):
        return _listen_vosk()
    else:
        print("\033[93m[WakeWord] Vosk model nahi mila — Google STT use kar raha hoon\033[0m")
        print(f"\033[93m[WakeWord] Model download karo: https://alphacephei.com/vosk/models\033[0m")
        print(f"\033[93m[WakeWord] Extract karo: {VOSK_MODEL_PATH}/\033[0m")
        return _listen_google()


def _listen_vosk() -> bool:
    """
    Vosk offline STT se wake word detect karo.
    Exact 'cracka' match karta hai — no internet needed.
    """
    try:
        import pyaudio
        from vosk import Model, KaldiRecognizer

        model = Model(VOSK_MODEL_PATH)

        # Sirf wake words ke liye grammar set karo
        # Yeh Vosk ko sirf inhi words dhundhne ko kehta hai
        grammar = json.dumps([
            "cracka", "crack a", "kraka",
            "jarvis", "hey jarvis", "mj", "baby",
            "[unk]"  # Unknown words ke liye
        ])
        rec = KaldiRecognizer(model, 16000, grammar)

        pa     = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )

        print("\033[90m[Waiting for wake word: 'Cracka'...]\033[0m")
        stream.start_stream()

        # 8 second tak suno
        import time
        end_time = time.time() + 8

        while time.time() < end_time:
            data = stream.read(4000, exception_on_overflow=False)

            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text   = result.get("text", "").lower().strip()

                if text and text != "[unk]":
                    print(f"\033[90m[Heard]: {text}\033[0m")

                    for word in WAKE_WORDS:
                        if word in text:
                            stream.stop_stream()
                            stream.close()
                            pa.terminate()
                            return True
            else:
                # Partial result check (faster response)
                partial = json.loads(rec.PartialResult())
                text    = partial.get("partial", "").lower().strip()

                if text:
                    for word in WAKE_WORDS:
                        if word in text and len(text) >= len(word):
                            print(f"\033[90m[Heard partial]: {text}\033[0m")
                            stream.stop_stream()
                            stream.close()
                            pa.terminate()
                            return True

        stream.stop_stream()
        stream.close()
        pa.terminate()
        return False

    except ImportError:
        print("[WakeWord] pyaudio not found — using Google STT")
        return _listen_google()
    except Exception as e:
        print(f"[WakeWord] Vosk error: {e} — using Google STT")
        return _listen_google()


def _listen_google() -> bool:
    """
    Google STT fallback — jab Vosk model nahi ho.
    'cracker' bhi accept karta hai kyunki Google yahi sunta hai.
    """
    import speech_recognition as sr

    GOOGLE_WAKE_WORDS = [
        "cracka", "cracker", "crack a", "kraka",
        "tracker", "jarvis", "hey jarvis", "mj",
    ]

    recognizer = sr.Recognizer()
    recognizer.energy_threshold         = 300
    recognizer.dynamic_energy_threshold = True
    recognizer.pause_threshold          = 0.5

    with sr.Microphone() as source:
        print("\033[90m[Waiting for wake word: 'Cracka'...]\033[0m")
        recognizer.adjust_for_ambient_noise(source, duration=0.3)

        try:
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
            text  = recognizer.recognize_google(
                audio, language="en-IN"
            ).lower().strip()

            print(f"\033[90m[Heard]: {text}\033[0m")

            for word in GOOGLE_WAKE_WORDS:
                if word in text:
                    return True

        except sr.WaitTimeoutError:
            pass
        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"[WakeWord] Google STT error: {e}")

    return False