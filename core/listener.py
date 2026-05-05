"""
core/listener.py - Fixed Version
Default: English only (no random Punjabi/Gujarati detection)
Voice switch: "Hindi mode" / "English mode" / "Auto mode"
"""

import speech_recognition as sr
import os
from core.logger import log_info, log_error

recognizer = sr.Recognizer()
recognizer.pause_threshold          = 0.6
recognizer.energy_threshold         = 300
recognizer.dynamic_energy_threshold = True

LANGUAGES = {
    "english":  "en-IN",
    "hindi":    "hi-IN",
    "marathi":  "mr-IN",
    "gujarati": "gu-IN",
    "tamil":    "ta-IN",
    "telugu":   "te-IN",
    "bengali":  "bn-IN",
    "punjabi":  "pa-IN",
    "kannada":  "kn-IN",
}

HINDI_WORDS = [
    "karo", "mujhe", "mera", "meri", "yeh", "woh", "nahi", "haan",
    "theek", "band", "kholo", "bolo", "batao", "chalao", "dikhao",
    "suno", "dekho", "kahan", "kaise", "kyun", "kaun", "kitna",
    "bahut", "accha", "zyada", "thoda", "abhi", "gaana", "bajao",
    "awaaz", "mausam", "yaad", "sunao", "bhejo", "karo"
]

HINDI_MAP = {
    "band karo": "shutdown", "restart karo": "restart",
    "so jao": "sleep", "lock karo": "lock",
    "battery kitni hai": "battery", "cpu kitna hai": "cpu usage",
    "ram kitni hai": "ram usage", "youtube kholo": "open youtube",
    "chrome kholo": "open chrome", "whatsapp kholo": "open whatsapp",
    "notepad kholo": "open notepad", "calculator kholo": "open calculator",
    "settings kholo": "open settings", "vscode kholo": "open vscode",
    "google karo": "search", "search karo": "search", "dhundho": "search",
    "gaana bajao": "play music", "music bajao": "play music",
    "gaana band karo": "stop music", "music band karo": "stop music",
    "screenshot lo": "take screenshot", "screenshot lelo": "take screenshot",
    "awaaz badao": "volume up", "awaaz kam karo": "volume down",
    "mute karo": "mute", "unmute karo": "unmute",
    "mausam batao": "weather", "mausam kaisa hai": "weather",
    "khabar sunao": "news", "news sunao": "news",
    "yaad rakho": "remember that", "kya yaad hai": "what do you remember",
    "sab bhool jao": "forget everything", "yaad dilao": "remind me",
    "reminder set karo": "set reminder", "network check karo": "check network",
    "face check karo": "face check", "apna chehra register karo": "register face",
    "ip address batao": "show my ip", "port scan karo": "scan ports",
    "file copy karo": "copy file", "file paste karo": "paste file",
    "file delete karo": "delete file", "folder banao": "create folder",
    "joke sunao": "joke", "mazhak sunao": "joke",
    "anuvad karo": "translate", "hisab karo": "calculate",
    "whatsapp message bhejo": "send whatsapp message",
    "email check karo": "check email", "form bharo": "fill the form",
    "form fill karo": "fill the form", "code review karo": "review my code",
    "screen dikha": "describe screen", "typing shuru karo": "start dictation",
    "tum kaun ho": "who are you", "tumhara naam kya hai": "what is your name",
    "tum kya kar sakte ho": "what can you do", "mera profile": "show profile",
    "config dikhao": "show config",
}

MODE_COMMANDS = {
    "hindi mode": "hindi", "english mode": "english",
    "auto mode": "auto", "marathi mode": "marathi",
    "gujarati mode": "gujarati", "tamil mode": "tamil",
    "telugu mode": "telugu", "bengali mode": "bengali",
    "punjabi mode": "punjabi", "kannada mode": "kannada",
}

# ── DEFAULT: english only — koi random language detect nahi hogi ──────────────
_current_mode = "english"


def _is_hinglish(text: str) -> bool:
    words = text.lower().split()
    return sum(1 for w in words if w in HINDI_WORDS) >= 1


def _translate_to_english(text: str) -> str:
    t = text.lower().strip()
    if t in HINDI_MAP:
        return HINDI_MAP[t]
    for phrase, english in HINDI_MAP.items():
        if phrase in t:
            return t.replace(phrase, english).strip()
    return t


def _check_mode_switch(text: str) -> bool:
    global _current_mode
    for cmd, mode in MODE_COMMANDS.items():
        if cmd in text.lower():
            _current_mode = mode
            log_info(f"Language mode → {mode}")
            return True
    return False


def listen(timeout: int = 8, phrase_limit: int = 10) -> str:
    global _current_mode

    with sr.Microphone() as source:
        print("\033[90m[Listening...]\033[0m")
        recognizer.adjust_for_ambient_noise(source, duration=0.3)
        try:
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_limit
            )
        except sr.WaitTimeoutError:
            return ""

    # Step 1: English try karo
    text_en = ""
    try:
        text_en = recognizer.recognize_google(audio, language="en-IN").strip()
        print(f"\033[93mBoss:\033[0m {text_en}")
    except sr.UnknownValueError:
        return ""  # Kuch nahi suna — STOP, doosri language mat try karo
    except sr.RequestError:
        return _vosk_fallback(audio)

    # Step 2: Mode switch check
    if _check_mode_switch(text_en):
        from core.voice_engine import speak
        speak(f"Switched to {_current_mode} mode Boss.")
        return ""

    # Step 3: English mode (default) — Hinglish support with translation
    if _current_mode == "english":
        if _is_hinglish(text_en):
            return _translate_to_english(text_en)
        return text_en.lower()

    # Step 4: Specific language mode
    if _current_mode not in ("auto", "english"):
        lang_code = LANGUAGES.get(_current_mode, "en-IN")
        try:
            text_r = recognizer.recognize_google(audio, language=lang_code).strip()
            print(f"\033[95mBoss ({_current_mode}):\033[0m {text_r}")
            return _translate_to_english(text_r)
        except Exception:
            return _translate_to_english(text_en)

    # Step 5: Auto mode — English + Hindi only (no other languages)
    if _current_mode == "auto":
        if _is_hinglish(text_en):
            try:
                text_hi = recognizer.recognize_google(audio, language="hi-IN").strip()
                print(f"\033[95mBoss (hindi):\033[0m {text_hi}")
                return _translate_to_english(text_hi)
            except Exception:
                pass
        return _translate_to_english(text_en)

    return text_en.lower()


def _vosk_fallback(audio) -> str:
    try:
        import vosk
    except ImportError:
        return ""
    try:
        from vosk import Model, KaldiRecognizer
        import json, wave, tempfile
        model_path = "models/vosk-model-small-en-us"
        if not os.path.exists(model_path):
            return ""
        model = Model(model_path)
        rec = KaldiRecognizer(model, 16000)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio.get_wav_data())
            tmp = f.name
        with wave.open(tmp, "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                rec.AcceptWaveform(data)
        os.unlink(tmp)
        result = json.loads(rec.FinalResult())
        text = result.get("text", "").strip()
        if text:
            print(f"\033[93mBoss (offline):\033[0m {text}")
        return text
    except Exception as e:
        log_error(f"Vosk error: {e}")
        return ""


def listen_for_text(prompt: str = "") -> str:
    if prompt:
        from core.voice_engine import speak
        speak(prompt)
    return listen()


def get_current_mode() -> str:
    return _current_mode


def set_language_mode(mode: str):
    global _current_mode
    if mode in LANGUAGES or mode in ("auto", "english"):
        _current_mode = mode