"""
core/offline_voice.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRACKA AI — Complete Offline Voice System
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features:
  ✅ Offline STT — Whisper (primary) + Vosk (fallback)
  ✅ Offline TTS — pyttsx3 (always offline)
  ✅ Noise cancellation — background noise filter
  ✅ Voice Activity Detection (VAD) — sirf tab sune jab koi bole
  ✅ Multiple microphone support — headset + laptop mic

Install:
  pip install openai-whisper        # Whisper STT
  pip install webrtcvad             # Voice Activity Detection
  pip install noisereduce           # Noise cancellation
  pip install sounddevice soundfile # Audio recording

Usage in listener.py:
  from core.offline_voice import offline_listen, offline_speak
  text = offline_listen()
  offline_speak("Hello Boss")
"""

import os
import sys
import json
import wave
import tempfile
import threading
import numpy as np
from core.logger import log_info, log_error
from core.config_loader import config

# ── Constants ─────────────────────────────────────────────────────────────────
SAMPLE_RATE    = 16000
CHANNELS       = 1
CHUNK_SIZE     = 1024
VAD_AGGRESSIVE = 2       # 0=least, 3=most aggressive filtering
SILENCE_LIMIT  = 1.5     # Seconds of silence before stopping
MAX_DURATION   = 12      # Max recording duration in seconds
VOSK_MODEL     = config.get("paths", "vosk_model",
                             default="models/vosk-model-small-en-us")

# Whisper model size — tradeoff between speed and accuracy
# tiny=fastest, base=good balance, small=more accurate, medium=best
WHISPER_MODEL  = config.get("ai_model", "whisper_model", default="base")

# Cache loaded models
_whisper_model = None
_vosk_model    = None


# ── 1. MICROPHONE MANAGER ─────────────────────────────────────────────────────

def list_microphones() -> list:
    """List all available microphones."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        mics    = []
        for i, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                mics.append({
                    "id":       i,
                    "name":     d["name"],
                    "channels": d["max_input_channels"],
                    "default":  i == sd.default.device[0]
                })
        return mics
    except Exception as e:
        log_error(f"Mic list error: {e}")
        return []


def get_best_microphone() -> int:
    """
    Auto-select best microphone.
    Prefers headset/USB mic over laptop built-in.
    """
    mics = list_microphones()
    if not mics:
        return None

    # Prefer headset/external mic
    priority_keywords = ["headset", "usb", "external", "blue", "rode",
                         "yeti", "hyperx", "steelseries", "logitech"]

    for mic in mics:
        name_lower = mic["name"].lower()
        for kw in priority_keywords:
            if kw in name_lower:
                log_info(f"Selected headset mic: {mic['name']}")
                return mic["id"]

    # Return default
    default = next((m for m in mics if m["default"]), mics[0])
    log_info(f"Selected default mic: {default['name']}")
    return default["id"]


def show_microphones() -> str:
    """Voice command: 'show microphones' """
    mics = list_microphones()
    if not mics:
        return "No microphones found Boss."

    lines = [f"Found {len(mics)} microphone(s) Boss:"]
    for m in mics:
        marker = " ← DEFAULT" if m["default"] else ""
        lines.append(f"  [{m['id']}] {m['name']}{marker}")
    return "\n".join(lines)


def set_microphone(mic_id: int):
    """Set active microphone by ID."""
    try:
        import sounddevice as sd
        sd.default.device[0] = mic_id
        mics = list_microphones()
        name = next((m["name"] for m in mics if m["id"] == mic_id), str(mic_id))
        log_info(f"Microphone set to: {name}")
        return f"Microphone changed to: {name} Boss."
    except Exception as e:
        return f"Could not set microphone Boss: {e}"


# ── 2. NOISE CANCELLATION ─────────────────────────────────────────────────────

def reduce_noise(audio: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """
    Remove background noise from audio using noisereduce.
    Falls back to simple high-pass filter if noisereduce not available.
    """
    try:
        import noisereduce as nr
        # Use first 0.5 seconds as noise profile
        noise_sample = audio[:int(sample_rate * 0.5)]
        cleaned      = nr.reduce_noise(
            y=audio,
            sr=sample_rate,
            y_noise=noise_sample,
            prop_decrease=0.8,
            stationary=False
        )
        log_info("Noise reduction applied")
        return cleaned

    except ImportError:
        # Simple high-pass filter fallback
        return _simple_highpass(audio, sample_rate)
    except Exception as e:
        log_error(f"Noise reduction error: {e}")
        return audio


def _simple_highpass(audio: np.ndarray, sr: int,
                      cutoff: float = 80.0) -> np.ndarray:
    """Simple high-pass filter to remove low-frequency noise."""
    try:
        from scipy import signal
        nyquist = sr / 2
        normal  = cutoff / nyquist
        b, a    = signal.butter(4, normal, btype="high", analog=False)
        return signal.filtfilt(b, a, audio).astype(np.float32)
    except Exception:
        return audio


# ── 3. VOICE ACTIVITY DETECTION (VAD) ────────────────────────────────────────

class VoiceActivityDetector:
    """
    Detects when someone is speaking.
    Stops recording when silence is detected.
    """

    def __init__(self, aggressiveness: int = VAD_AGGRESSIVE):
        self._vad     = None
        self._ready   = False
        self._aggr    = aggressiveness
        self._init()

    def _init(self):
        try:
            import webrtcvad
            self._vad   = webrtcvad.Vad(self._aggr)
            self._ready = True
            log_info(f"VAD initialized (aggressiveness={self._aggr})")
        except ImportError:
            log_info("webrtcvad not available — using energy-based VAD")
        except Exception as e:
            log_error(f"VAD init error: {e}")

    def is_speech(self, frame: bytes, sample_rate: int = 16000) -> bool:
        """Check if audio frame contains speech."""
        if self._vad and self._ready:
            try:
                return self._vad.is_speech(frame, sample_rate)
            except Exception:
                pass
        # Fallback: energy-based detection
        return self._energy_vad(frame)

    def _energy_vad(self, frame: bytes) -> bool:
        """Simple energy-based voice detection."""
        audio = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
        energy = np.sqrt(np.mean(audio ** 2))
        return energy > 500  # Threshold


# Global VAD instance
_vad = VoiceActivityDetector()


# ── 4. SMART AUDIO RECORDER ──────────────────────────────────────────────────

def record_until_silence(mic_id: int = None,
                          silence_limit: float = SILENCE_LIMIT,
                          max_duration: float = MAX_DURATION) -> np.ndarray:
    """
    Record audio until silence is detected.
    Returns numpy array of audio data.
    """
    try:
        import sounddevice as sd

        if mic_id is None:
            mic_id = get_best_microphone()

        print("\033[90m[Listening...]\033[0m")

        frames         = []
        silence_frames = 0
        speech_started = False
        max_frames     = int(max_duration * SAMPLE_RATE / CHUNK_SIZE)
        silence_thresh = int(silence_limit * SAMPLE_RATE / CHUNK_SIZE)

        def callback(indata, frame_count, time_info, status):
            nonlocal silence_frames, speech_started
            frame_bytes = (indata * 32767).astype(np.int16).tobytes()
            frames.append(indata.copy())

            if _vad.is_speech(frame_bytes):
                speech_started = True
                silence_frames = 0
            elif speech_started:
                silence_frames += 1

        with sd.InputStream(
            device=mic_id,
            channels=CHANNELS,
            samplerate=SAMPLE_RATE,
            blocksize=CHUNK_SIZE,
            dtype=np.float32,
            callback=callback
        ):
            import time
            start = time.time()
            while True:
                time.sleep(0.05)
                elapsed = time.time() - start

                # Stop conditions
                if speech_started and silence_frames >= silence_thresh:
                    break
                if elapsed >= max_duration:
                    break
                if elapsed > 2 and not speech_started:
                    # No speech detected in 2 seconds
                    break

        if not frames:
            return np.array([], dtype=np.float32)

        audio = np.concatenate(frames, axis=0).flatten()
        return audio

    except ImportError:
        log_error("sounddevice not installed: pip install sounddevice")
        return np.array([], dtype=np.float32)
    except Exception as e:
        log_error(f"Recording error: {e}")
        return np.array([], dtype=np.float32)


# ── 5. WHISPER STT ────────────────────────────────────────────────────────────

def _load_whisper():
    """Load Whisper model (cached after first load)."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            log_info(f"Loading Whisper model: {WHISPER_MODEL}")
            _whisper_model = whisper.load_model(WHISPER_MODEL)
            log_info("Whisper model loaded!")
        except ImportError:
            log_error("Whisper not installed: pip install openai-whisper")
        except Exception as e:
            log_error(f"Whisper load error: {e}")
    return _whisper_model


def transcribe_whisper(audio: np.ndarray) -> str:
    """
    Transcribe audio using OpenAI Whisper (offline).
    Very accurate, supports multiple languages.
    """
    model = _load_whisper()
    if model is None:
        return ""

    try:
        # Whisper needs float32 normalized to [-1, 1]
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        if np.max(np.abs(audio)) > 1.0:
            audio = audio / 32768.0

        # Save to temp file (Whisper needs file input)
        with tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as f:
            tmp_path = f.name

        import soundfile as sf
        sf.write(tmp_path, audio, SAMPLE_RATE)

        # Transcribe
        result = model.transcribe(
            tmp_path,
            language=None,          # Auto-detect language
            task="transcribe",
            fp16=False,             # CPU mode
            verbose=False
        )

        os.unlink(tmp_path)
        text = result["text"].strip()
        log_info(f"Whisper transcribed: {text[:50]}")
        return text

    except Exception as e:
        log_error(f"Whisper transcribe error: {e}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return ""


# ── 6. VOSK STT FALLBACK ──────────────────────────────────────────────────────

def _load_vosk():
    """Load Vosk model (cached)."""
    global _vosk_model
    if _vosk_model is None:
        try:
            from vosk import Model
            if os.path.exists(VOSK_MODEL):
                _vosk_model = Model(VOSK_MODEL)
                log_info("Vosk model loaded!")
            else:
                log_error(f"Vosk model not found: {VOSK_MODEL}")
        except Exception as e:
            log_error(f"Vosk load error: {e}")
    return _vosk_model


def transcribe_vosk(audio: np.ndarray) -> str:
    """Transcribe audio using Vosk (offline fallback)."""
    model = _load_vosk()
    if model is None:
        return ""

    try:
        from vosk import KaldiRecognizer

        rec = KaldiRecognizer(model, SAMPLE_RATE)

        # Convert to int16 bytes
        if audio.dtype == np.float32:
            audio_int = (audio * 32767).astype(np.int16)
        else:
            audio_int = audio.astype(np.int16)

        audio_bytes = audio_int.tobytes()

        # Process in chunks
        chunk_size = SAMPLE_RATE * 2  # 1 second chunks
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i + chunk_size]
            rec.AcceptWaveform(chunk)

        result = json.loads(rec.FinalResult())
        text   = result.get("text", "").strip()
        log_info(f"Vosk transcribed: {text[:50]}")
        return text

    except Exception as e:
        log_error(f"Vosk transcribe error: {e}")
        return ""


# ── 7. MAIN OFFLINE LISTENER ──────────────────────────────────────────────────

def offline_listen(mic_id: int = None) -> str:
    """
    Main offline voice listener.
    Uses: Whisper → Vosk fallback → Google fallback
    Returns recognized text.
    """
    # Record audio with VAD
    audio = record_until_silence(mic_id=mic_id)

    if len(audio) < SAMPLE_RATE * 0.3:
        # Too short — probably silence
        return ""

    # Apply noise reduction
    audio = reduce_noise(audio)

    # Try Whisper first (most accurate)
    text = transcribe_whisper(audio)

    # Vosk fallback
    if not text:
        log_info("Whisper failed — trying Vosk")
        text = transcribe_vosk(audio)

    # Google fallback (if online)
    if not text:
        log_info("Vosk failed — trying Google STT")
        text = _google_fallback(audio)

    if text:
        print(f"\033[93mBoss:\033[0m {text}")

    return text.lower().strip()


def _google_fallback(audio: np.ndarray) -> str:
    """Last resort: Google STT."""
    try:
        import speech_recognition as sr
        import soundfile as sf

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp = f.name
        sf.write(tmp, audio, SAMPLE_RATE)

        r         = sr.Recognizer()
        with sr.AudioFile(tmp) as source:
            audio_data = r.record(source)
        os.unlink(tmp)

        return r.recognize_google(audio_data, language="en-IN")
    except Exception:
        return ""


# ── 8. OFFLINE TTS ────────────────────────────────────────────────────────────

def offline_speak(text: str, rate: int = 160, volume: float = 1.0):
    """
    Offline text-to-speech using pyttsx3.
    Works without internet — always available.
    """
    print(f"\033[96mCracka:\033[0m {text}")

    def _speak():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate",   rate)
            engine.setProperty("volume", volume)

            # Best voice select karo
            voices = engine.getProperty("voices")
            for v in voices:
                if any(x in v.name.lower() for x in
                       ["zira", "david", "heera", "ravi"]):
                    engine.setProperty("voice", v.id)
                    break

            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            log_error(f"Offline TTS error: {e}")
            # PowerShell fallback (Windows)
            try:
                safe = text.replace('"', "")[:200]
                os.system(
                    f'PowerShell -Command "Add-Type -AssemblyName System.Speech; '
                    f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                    f'$s.Rate = 1; $s.Speak(\\"{safe}\\")"'
                )
            except Exception:
                pass

    t = threading.Thread(target=_speak, daemon=True)
    t.start()


# ── 9. INTERNET CHECK ─────────────────────────────────────────────────────────

def is_online() -> bool:
    """Check if internet is available."""
    try:
        import requests
        requests.get("https://www.google.com", timeout=2)
        return True
    except Exception:
        return False


def smart_listen() -> str:
    """
    Automatically choose best STT based on internet availability.
    Online  → Google STT (faster)
    Offline → Whisper + Vosk
    """
    if is_online():
        # Use Google STT (faster when online)
        try:
            import speech_recognition as sr
            r   = sr.Recognizer()
            r.pause_threshold          = 0.6
            r.dynamic_energy_threshold = True

            mic_id = get_best_microphone()

            with sr.Microphone(device_index=mic_id) as source:
                print("\033[90m[Listening (online)...]\033[0m")
                r.adjust_for_ambient_noise(source, duration=0.3)
                try:
                    audio = r.listen(source, timeout=8, phrase_time_limit=10)
                    text  = r.recognize_google(audio, language="en-IN")
                    print(f"\033[93mBoss:\033[0m {text}")
                    return text.lower().strip()
                except Exception:
                    pass
        except Exception:
            pass

    # Offline mode
    log_info("Using offline STT")
    return offline_listen()


# ── 10. VOICE COMMANDS ────────────────────────────────────────────────────────

def switch_microphone_voice(command: str) -> str:
    """
    Voice command: 'switch microphone' or 'change mic'
    Shows available mics and lets Boss choose.
    """
    from core.voice_engine import speak
    from core.listener import listen_for_text

    mics_str = show_microphones()
    speak(mics_str)

    choice = listen_for_text("Which microphone number Boss?")
    try:
        mic_id = int("".join(filter(str.isdigit, choice)))
        return set_microphone(mic_id)
    except Exception:
        return "Could not understand the microphone number Boss."