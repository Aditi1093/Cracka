"""
intelligence/face_mood_detector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Camera se Boss ka mood detect karo.
Uses: OpenCV + DeepFace / MediaPipe
"""

import cv2
import os
from core.logger import log_info, log_error
from datetime import datetime


def detect_face_mood() -> str:
    """
    Camera kholo, Boss ka chehra dekho, mood batao.
    Returns emotion string.
    """
    # Try DeepFace first (most accurate)
    try:
        from deepface import DeepFace
        return _detect_with_deepface()
    except ImportError:
        pass

    # Fallback: MediaPipe
    try:
        return _detect_with_mediapipe()
    except ImportError:
        pass

    return "Could not detect mood Boss. Please install deepface: pip install deepface"


def _detect_with_deepface() -> str:
    """DeepFace se mood detect karo — most accurate."""
    from deepface import DeepFace

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    from core.voice_engine import speak
    speak("Looking at your face Boss. Hold still for a moment.")

    import time
    time.sleep(1.5)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return "Could not capture face Boss."

    # Save temp image
    os.makedirs("data", exist_ok=True)
    img_path = "data/face_temp.jpg"
    cv2.imwrite(img_path, frame)

    try:
        result   = DeepFace.analyze(
            img_path,
            actions=["emotion", "age", "gender"],
            enforce_detection=False,
            silent=True
        )

        if isinstance(result, list):
            result = result[0]

        dominant = result.get("dominant_emotion", "neutral")
        emotions = result.get("emotion", {})
        age      = result.get("age", "unknown")
        gender   = result.get("dominant_gender", "unknown")

        # Sort emotions by confidence
        top3 = sorted(emotions.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = ", ".join([f"{e}: {v:.0f}%" for e, v in top3])

        log_info(f"Face mood detected: {dominant}")

        # Save to mood tracker
        try:
            from memory.memory_manager import track_mood
            track_mood(dominant)
        except Exception:
            pass

        response = (
            f"Boss, I can see you look {dominant}! "
            f"Top emotions: {top3_str}. "
            f"Estimated age: {age}, Gender: {gender}."
        )

        # Motivational response based on mood
        mood_responses = {
            "happy":    "You're looking happy Boss! Great energy today!",
            "sad":      "You seem sad Boss. Is everything okay? I'm here.",
            "angry":    "You look stressed Boss. Take a deep breath.",
            "surprised": "You look surprised Boss! Something exciting happened?",
            "fear":     "You seem worried Boss. What's on your mind?",
            "disgust":  "Something bothering you Boss?",
            "neutral":  "You look calm and focused Boss. Ready to work!",
        }

        extra = mood_responses.get(dominant.lower(), "")
        if extra:
            response += f" {extra}"

        # Cleanup
        if os.path.exists(img_path):
            os.remove(img_path)

        return response

    except Exception as e:
        log_error(f"DeepFace error: {e}")
        if os.path.exists(img_path):
            os.remove(img_path)
        return f"Could not analyze face Boss. Error: {e}"


def _detect_with_mediapipe() -> str:
    """MediaPipe se basic face detection."""
    import mediapipe as mp

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    mp_face = mp.solutions.face_detection
    detector = mp_face.FaceDetection(min_detection_confidence=0.5)

    import time
    time.sleep(1)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return "Could not capture frame Boss."

    rgb    = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = detector.process(rgb)

    if result.detections:
        count = len(result.detections)
        return f"I can see {count} face(s) Boss. Install deepface for emotion detection: pip install deepface"

    return "No face detected Boss. Make sure you are in front of the camera."


def continuous_mood_monitor(duration_secs: int = 30) -> str:
    """
    Monitor Boss's mood for N seconds continuously.
    Takes a snapshot every 10 seconds.
    """
    from core.voice_engine import speak
    import time

    speak(f"Monitoring your mood for {duration_secs} seconds Boss.")

    moods    = []
    end_time = time.time() + duration_secs

    while time.time() < end_time:
        try:
            from deepface import DeepFace
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()

            if ret:
                os.makedirs("data", exist_ok=True)
                path = "data/face_temp.jpg"
                cv2.imwrite(path, frame)
                result = DeepFace.analyze(path, actions=["emotion"],
                                          enforce_detection=False, silent=True)
                if isinstance(result, list):
                    result = result[0]
                mood = result.get("dominant_emotion", "neutral")
                moods.append(mood)
                if os.path.exists(path):
                    os.remove(path)
        except Exception:
            pass
        time.sleep(10)

    if not moods:
        return "Could not monitor mood Boss."

    from collections import Counter
    dominant = Counter(moods).most_common(1)[0][0]
    return (f"Mood monitoring complete Boss! "
            f"Dominant mood: {dominant}. "
            f"Readings: {', '.join(moods)}")