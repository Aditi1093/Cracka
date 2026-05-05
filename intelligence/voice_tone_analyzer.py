"""
intelligence/voice_tone_analyzer.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Awaaz se emotion aur tone detect karo.
Uses: librosa (audio analysis) + numpy
"""

import os
import numpy as np
from core.logger import log_info, log_error


def analyze_voice_tone(audio_data=None, audio_path: str = None) -> dict:
    """
    Audio se tone features extract karo.
    Returns dict with emotion, energy, pitch, speed.
    """
    try:
        import librosa
        import sounddevice as sd
        import soundfile as sf

        # Record if no audio provided
        if audio_path is None and audio_data is None:
            audio_data, sample_rate = _record_audio(duration=3)
        elif audio_path:
            audio_data, sample_rate = librosa.load(audio_path, sr=22050)
        else:
            sample_rate = 22050

        return _extract_features(audio_data, sample_rate)

    except ImportError as e:
        log_error(f"Voice analysis library missing: {e}")
        return {"emotion": "unknown", "error": str(e)}
    except Exception as e:
        log_error(f"Voice analysis error: {e}")
        return {"emotion": "neutral", "error": str(e)}


def _record_audio(duration: int = 3, sample_rate: int = 22050) -> tuple:
    """Record audio from microphone."""
    import sounddevice as sd
    audio = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32"
    )
    sd.wait()
    return audio.flatten(), sample_rate


def _extract_features(audio: np.ndarray, sr: int) -> dict:
    """Extract audio features and classify emotion."""
    import librosa

    result = {
        "emotion":    "neutral",
        "energy":     "normal",
        "pitch":      "normal",
        "speed":      "normal",
        "confidence": 0.0
    }

    try:
        # 1. Energy (loudness)
        rms   = librosa.feature.rms(y=audio)[0]
        energy_mean = float(np.mean(rms))

        if energy_mean > 0.08:
            result["energy"] = "high"
        elif energy_mean < 0.02:
            result["energy"] = "low"
        else:
            result["energy"] = "normal"

        # 2. Pitch (fundamental frequency)
        f0, voiced, _ = librosa.pyin(
            audio, fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7")
        )
        valid_f0 = f0[voiced] if voiced is not None else np.array([])
        pitch_mean = float(np.nanmean(valid_f0)) if len(valid_f0) > 0 else 150.0

        if pitch_mean > 250:
            result["pitch"] = "high"
        elif pitch_mean < 120:
            result["pitch"] = "low"
        else:
            result["pitch"] = "normal"

        # 3. Speaking rate (zero crossing rate)
        zcr  = librosa.feature.zero_crossing_rate(audio)[0]
        zcr_mean = float(np.mean(zcr))

        if zcr_mean > 0.12:
            result["speed"] = "fast"
        elif zcr_mean < 0.05:
            result["speed"] = "slow"
        else:
            result["speed"] = "normal"

        # 4. MFCC features for emotion classification
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfcc, axis=1)

        # Rule-based emotion from features
        emotion, confidence = _classify_emotion(
            energy_mean, pitch_mean, zcr_mean, mfcc_mean
        )
        result["emotion"]    = emotion
        result["confidence"] = confidence

        log_info(f"Voice tone: {emotion} (energy={result['energy']}, "
                 f"pitch={result['pitch']}, speed={result['speed']})")

    except Exception as e:
        log_error(f"Feature extraction error: {e}")

    return result


def _classify_emotion(energy: float, pitch: float,
                       zcr: float, mfcc: np.ndarray) -> tuple:
    """Classify emotion from audio features."""
    scores = {
        "happy":   0.0,
        "sad":     0.0,
        "angry":   0.0,
        "neutral": 0.0,
        "excited": 0.0,
        "tired":   0.0,
    }

    # High energy + high pitch + fast = excited/happy
    if energy > 0.08 and pitch > 200 and zcr > 0.10:
        scores["excited"] += 2.0
        scores["happy"]   += 1.5

    # High energy + low pitch + fast = angry
    elif energy > 0.07 and pitch < 150 and zcr > 0.10:
        scores["angry"] += 2.5

    # Low energy + low pitch + slow = sad/tired
    elif energy < 0.03 and pitch < 140 and zcr < 0.06:
        scores["sad"]   += 1.5
        scores["tired"] += 1.5

    # Normal energy + normal pitch = neutral/happy
    elif 0.03 <= energy <= 0.07 and 150 <= pitch <= 220:
        scores["neutral"] += 2.0
        scores["happy"]   += 0.5

    # Low energy, slow = tired
    elif energy < 0.04 and zcr < 0.07:
        scores["tired"] += 2.0

    else:
        scores["neutral"] += 1.5

    best       = max(scores, key=scores.get)
    confidence = min(scores[best] / 3.0, 1.0)

    return best, round(confidence, 2)


def get_voice_emotion_string(audio_data=None) -> str:
    """
    Voice tone se emotion string return karo.
    Cracka ke responses ke liye use hota hai.
    """
    result = analyze_voice_tone(audio_data=audio_data)
    emotion = result.get("emotion", "neutral")
    energy  = result.get("energy", "normal")
    speed   = result.get("speed", "normal")

    response_parts = [f"Voice tone analysis Boss:"]
    response_parts.append(f"  Emotion: {emotion.upper()}")
    response_parts.append(f"  Energy level: {energy}")
    response_parts.append(f"  Speaking speed: {speed}")

    # Combine with text emotion for better accuracy
    conf = result.get("confidence", 0)
    if conf > 0.5:
        response_parts.append(f"  Confidence: {int(conf*100)}%")

    return "\n".join(response_parts)