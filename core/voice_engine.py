"""
core/voice_engine.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Text-to-Speech engine for Cracka AI.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WHY THIS VERSION CHANGED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CRASH FIX (kept from previous version): ONE persistent pyttsx3
   engine on a SINGLE dedicated worker thread, processed via a queue.
   Repeated pyttsx3.init() across threads was corrupting Windows COM
   state and silently killing the whole process.

2. MULTILINGUAL MALE VOICES: gTTS only offers a single (female) voice
   per language. Switched non-English speech to edge-tts (Microsoft
   Edge's free, no-API-key TTS), which offers Neural voices in 100+
   languages/locales, INCLUDING male options for almost every
   language (e.g. Hindi -> hi-IN-MadhurNeural (male) /
   hi-IN-SwaraNeural (female), French -> fr-FR-HenriNeural (male),
   Japanese -> ja-JP-KeitaNeural (male), Russian -> ru-RU-DmitryNeural
   (male), etc.) Quality is also noticeably better than gTTS.

3. SIMPLER & MORE ROBUST PLAYBACK: edge-tts streams audio that we save
   as mp3 and play via the Windows Media Player COM object through
   PowerShell (same approach as the previous Windows fallback) -
   avoids pygame/SDL entirely, removing that whole crash surface.

4. English still uses pyttsx3 (David, male) - fast, offline, no
   change in behavior for the most common case.

Install:
    pip install edge-tts

Public API UNCHANGED: speak(text, wait=False), speak_gtts(text, lang)
[kept as a thin compatibility alias -> now uses edge-tts internally],
set_voice_speed(rate), is_speaking().
"""

import pyttsx3
import threading
import queue
import os
import re
import time
import asyncio

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE -> EDGE-TTS MALE VOICE MAP
# Picked a male Neural voice for each language Cracka's translator
# supports (see utils/translator.py LANG_CODES). Falls back to a
# generic English male voice if a language isn't in this map.
# ─────────────────────────────────────────────────────────────────────────────
EDGE_VOICE_MAP = {
    "hi":    "hi-IN-MadhurNeural",      # Hindi (male)
    "mr":    "mr-IN-ManoharNeural",     # Marathi (male)
    "fr":    "fr-FR-HenriNeural",       # French (male)
    "es":    "es-ES-AlvaroNeural",      # Spanish (male)
    "de":    "de-DE-ConradNeural",      # German (male)
    "ja":    "ja-JP-KeitaNeural",       # Japanese (male)
    "zh-CN": "zh-CN-YunxiNeural",       # Chinese (male)
    "ar":    "ar-SA-HamedNeural",       # Arabic (male)
    "pt":    "pt-PT-DuarteNeural",      # Portuguese (male)
    "ru":    "ru-RU-DmitryNeural",      # Russian (male)
    "it":    "it-IT-DiegoNeural",       # Italian (male)
    "ko":    "ko-KR-InJoonNeural",      # Korean (male)
    "gu":    "gu-IN-NiranjanNeural",    # Gujarati (male)
    "ta":    "ta-IN-ValluvarNeural",    # Tamil (male)
    "te":    "te-IN-MohanNeural",       # Telugu (male)
    "bn":    "bn-IN-BashkarNeural",     # Bengali (male)
    "pa":    "hi-IN-MadhurNeural",      # Punjabi - no dedicated male voice, use Hindi male
    "ur":    "ur-PK-AsadNeural",        # Urdu (male)
    "ml":    "ml-IN-MidhunNeural",      # Malayalam (male)
    "kn":    "kn-IN-GaganNeural",       # Kannada (male)
    "or":    "or-IN-SukantNeural",      # Odia (male)
    "vi":    "vi-VN-NamMinhNeural",     # Vietnamese (male)
    "th":    "th-TH-NiwatNeural",       # Thai (male)
    "tr":    "tr-TR-AhmetNeural",       # Turkish (male)
    "pl":    "pl-PL-MarekNeural",       # Polish (male)
    "nl":    "nl-NL-MaartenNeural",     # Dutch (male)
    "el":    "el-GR-NestorasNeural",    # Greek (male)
    "iw":    "he-IL-AvriNeural",        # Hebrew (male)
    "id":    "id-ID-ArdiNeural",        # Indonesian (male)
    "uk":    "uk-UA-OstapNeural",       # Ukrainian (male)
    "fa":    "fa-IR-FaridNeural",       # Persian (male)
    "en":    "en-US-GuyNeural",         # English (male, edge-tts variant)
}

DEFAULT_EDGE_VOICE = "en-US-GuyNeural"


# ─────────────────────────────────────────────────────────────────────────────
# SCRIPT-BASED LANGUAGE DETECTION
# Same heuristic as utils/translator.py's detect_language(), returns a
# code that maps into EDGE_VOICE_MAP.
# ─────────────────────────────────────────────────────────────────────────────
_SCRIPT_RANGES = [
    (r"[\u0900-\u097F]", "hi"),   # Devanagari - Hindi/Marathi
    (r"[\u0A80-\u0AFF]", "gu"),   # Gujarati
    (r"[\u0B80-\u0BFF]", "ta"),   # Tamil
    (r"[\u0C00-\u0C7F]", "te"),   # Telugu
    (r"[\u0980-\u09FF]", "bn"),   # Bengali
    (r"[\u0A00-\u0A7F]", "pa"),   # Punjabi (Gurmukhi)
    (r"[\u0D00-\u0D7F]", "ml"),   # Malayalam
    (r"[\u0C80-\u0CFF]", "kn"),   # Kannada
    (r"[\u0600-\u06FF]", "ar"),   # Arabic / Urdu / Persian script
    (r"[\u4e00-\u9fff]", "zh-CN"),# Chinese
    (r"[\u3040-\u30ff]", "ja"),   # Japanese
    (r"[\uac00-\ud7a3]", "ko"),   # Korean
    (r"[\u0e00-\u0e7f]", "th"),   # Thai
    (r"[\u0370-\u03ff]", "el"),   # Greek
    (r"[\u0400-\u04ff]", "ru"),   # Cyrillic
]


def _detect_speech_lang(text: str) -> str:
    """Returns a language code (key into EDGE_VOICE_MAP) for non-Latin
    scripts, else None (meaning: plain English/Latin, use pyttsx3)."""
    for pattern, code in _SCRIPT_RANGES:
        if re.search(pattern, text):
            return code
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE PERSISTENT SPEECH WORKER
# ─────────────────────────────────────────────────────────────────────────────
_speech_queue = queue.Queue()
_worker_thread = None
_worker_lock = threading.Lock()
_speaking = False

# Persistent pyttsx3 engine - created once, on the worker thread,
# reused for every English speak() call.
_pyttsx3_engine = None


def _init_pyttsx3_engine():
    """Create and configure the persistent pyttsx3 engine. MUST be
    called from the worker thread (so COM is initialized there)."""
    global _pyttsx3_engine
    try:
        eng = pyttsx3.init()
        eng.setProperty('rate', 160)
        eng.setProperty('volume', 1.0)

        voices = eng.getProperty('voices')
        for v in voices:
            vname = v.name.lower()
            # Prefer David (male) for English; Zira as fallback
            if 'david' in vname:
                eng.setProperty('voice', v.id)
                break
            if 'zira' in vname:
                eng.setProperty('voice', v.id)

        _pyttsx3_engine = eng
    except Exception as e:
        print(f"[Voice] Could not initialize pyttsx3 engine: {e}")
        _pyttsx3_engine = None


def _worker_loop():
    """
    Runs forever on a single dedicated thread. Initializes the
    persistent pyttsx3 engine ONCE, then processes the speech queue
    one item at a time - never overlapping, never re-initializing COM.
    """
    global _speaking

    _init_pyttsx3_engine()

    while True:
        item = _speech_queue.get()
        if item is None:
            continue

        text, lang_code = item
        _speaking = True

        try:
            if lang_code:
                _speak_edge_tts_blocking(text, lang_code)
            else:
                _speak_pyttsx3_blocking(text)
        except Exception as e:
            print(f"[Voice] Worker error: {e}")
        finally:
            _speaking = False
            _speech_queue.task_done()


def _ensure_worker_running():
    """Start the worker thread if it isn't already running (also
    restarts it if it died unexpectedly)."""
    global _worker_thread
    with _worker_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
            _worker_thread.start()


# ─────────────────────────────────────────────────────────────────────────────
# PYTTSX3 - ENGLISH SPEECH (reuses the single persistent engine)
# ─────────────────────────────────────────────────────────────────────────────

def _speak_pyttsx3_blocking(text: str):
    """Speak English text using the persistent pyttsx3 engine."""
    global _pyttsx3_engine

    if _pyttsx3_engine is None:
        _init_pyttsx3_engine()

    if _pyttsx3_engine is not None:
        try:
            _pyttsx3_engine.say(text)
            _pyttsx3_engine.runAndWait()
            return
        except Exception as e:
            print(f"[Voice] pyttsx3 error: {e}")
            _pyttsx3_engine = None

    # Last resort: PowerShell SAPI fallback (no COM/pyttsx3 involved)
    try:
        safe = text.replace('"', '').replace("'", '')[:200]
        os.system(
            f'PowerShell -Command "Add-Type -AssemblyName System.Speech; '
            f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
            f'$s.Rate = 1; $s.Speak(\\"{safe}\\")"'
        )
    except Exception as e2:
        print(f"[Voice] Fallback also failed: {e2}")


# ─────────────────────────────────────────────────────────────────────────────
# EDGE-TTS - MULTILINGUAL MALE-VOICE SPEECH
# ─────────────────────────────────────────────────────────────────────────────

def _speak_edge_tts_blocking(text: str, lang_code: str):
    """
    Speak non-English (or explicitly-requested) text via edge-tts,
    using a male Neural voice for the detected language. Saves audio
    to a temp mp3 and plays it via the Windows Media Player COM object
    (PowerShell) - avoids pygame/SDL entirely.

    Falls back to the persistent pyttsx3 engine (English voice
    attempting the text) if edge-tts fails (e.g. no internet).
    """
    tmp = None
    try:
        import edge_tts
        import tempfile

        voice = EDGE_VOICE_MAP.get(lang_code, DEFAULT_EDGE_VOICE)

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tmp = f.name

        # edge-tts is async - run it synchronously here since this
        # whole function executes on the dedicated worker thread.
        async def _generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp)

        asyncio.run(_generate())

        _play_mp3_via_windows(tmp)

    except ImportError:
        print("[Voice] edge-tts not installed: pip install edge-tts "
              "- falling back to English voice for non-English text.")
        _speak_pyttsx3_blocking(text)
    except Exception as e:
        print(f"[Voice] edge-tts error ({e}) - falling back to English voice.")
        _speak_pyttsx3_blocking(text)
    finally:
        if tmp and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def _play_mp3_via_windows(mp3_path: str):
    """
    Play an mp3 file synchronously using a WPF MediaPlayer COM object
    via PowerShell, blocking until playback finishes. Avoids
    pygame/SDL entirely (the source of earlier silent crashes).
    """
    try:
        ps_script = (
            "Add-Type -AssemblyName presentationCore; "
            "$player = New-Object system.windows.media.mediaplayer; "
            f"$player.open([uri]'{mp3_path}'); "
            "$player.Play(); "
            "Start-Sleep -Milliseconds 300; "
            "$timeout = 0; "
            "while ($player.NaturalDuration.HasTimeSpan -eq $false -and $timeout -lt 50) "
            "{ Start-Sleep -Milliseconds 100; $timeout++ }; "
            "if ($player.NaturalDuration.HasTimeSpan) "
            "{ $dur = $player.NaturalDuration.TimeSpan.TotalMilliseconds; "
            "Start-Sleep -Milliseconds ([int]$dur + 200) } "
            "else { Start-Sleep -Milliseconds 3000 }; "
            "$player.Close()"
        )
        os.system(f'PowerShell -WindowStyle Hidden -Command "{ps_script}"')
    except Exception as e:
        print(f"[Voice] Windows mp3 playback error: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def speak(text: str, wait: bool = False):
    """
    Queue text to be spoken. Automatically picks the right engine:
      - Non-English script (Hindi, Tamil, Arabic, etc.) -> edge-tts
        with a male Neural voice for that language
      - English/Latin script -> pyttsx3 (persistent engine, David/male,
        offline)

    Non-blocking by default - text is queued and the single speech
    worker thread processes it. wait=True blocks until the queue has
    been fully drained.
    """
    print(f"\033[96mCracka:\033[0m {text}")

    if not text or not text.strip():
        return

    _ensure_worker_running()

    lang_code = _detect_speech_lang(text)
    _speech_queue.put((text, lang_code))

    if wait:
        _speech_queue.join()


def speak_gtts(text: str, lang: str = "en"):
    """
    BACKWARD-COMPATIBLE alias. Despite the name (kept so existing
    callers don't break), this now routes through edge-tts for
    non-English `lang` codes, using the male voice map above, and
    through pyttsx3 for English.
    """
    print(f"\033[96mCracka:\033[0m {text}")
    _ensure_worker_running()

    if lang == "en":
        _speech_queue.put((text, None))
    else:
        _speech_queue.put((text, lang))


def set_voice_speed(rate: int = 160):
    """
    Update the speech rate for the pyttsx3 (English) engine. edge-tts
    rate isn't adjusted here; pass SSML rate tags to edge_tts.Communicate
    if needed in the future.
    """
    os.environ['CRACKA_VOICE_RATE'] = str(rate)
    if _pyttsx3_engine is not None:
        try:
            _pyttsx3_engine.setProperty('rate', rate)
        except Exception:
            pass


def is_speaking() -> bool:
    return _speaking