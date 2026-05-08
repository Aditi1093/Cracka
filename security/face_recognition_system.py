"""
security/face_recognition_system.py
Uses ONLY OpenCV — No MediaPipe, No dlib, No TensorFlow!
"""

import cv2
import os
import json
import numpy as np
from datetime import datetime

try:
    from core.logger import log_info, log_error
except:
    def log_info(x): print(f"[INFO] {x}")
    def log_error(x): print(f"[ERROR] {x}")

BOSS_PHOTO     = "data/boss.jpg"
BOSS_DATA_FILE = "data/boss_face_data.json"
os.makedirs("data", exist_ok=True)

CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade = cv2.CascadeClassifier(CASCADE_PATH)


def _detect_faces(frame):
    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
    )
    return faces, gray


def _get_embedding(frame, x, y, w, h):
    gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    face_roi = gray[y:y+h, x:x+w]
    face_roi = cv2.resize(face_roi, (128, 128))
    face_roi = cv2.equalizeHist(face_roi)
    return face_roi.flatten().astype(np.float32)


def _compare(saved_emb, current_emb):
    try:
        a1 = np.array(saved_emb,   dtype=np.float32)
        a2 = np.array(current_emb, dtype=np.float32)
        a1 = a1 / (np.linalg.norm(a1) + 1e-8)
        a2 = a2 / (np.linalg.norm(a2) + 1e-8)
        dist  = float(np.linalg.norm(a1 - a2))
        conf  = max(0.0, round((1.0 - dist) * 100, 1))
        match = dist < 0.35
        return match, conf
    except Exception as e:
        log_error(f"Compare error: {e}")
        return False, 0.0


def register_boss_face():
    try:
        from core.voice_engine import speak
    except:
        def speak(x): print(f"Cracka: {x}")

    speak("Look at the camera Boss. Capturing in 3 seconds.")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    import time
    time.sleep(2)

    best_frame = None
    best_faces = []
    start      = time.time()

    while time.time() - start < 8:
        ret, frame = cap.read()
        if not ret:
            break

        faces, _ = _detect_faces(frame)

        if len(faces) > 0:
            best_frame = frame.copy()
            best_faces = list(faces)
            for (x, y, w, h) in faces:
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.putText(frame, "Hold still...", (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "Looking for face...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        cv2.imshow("Cracka - Register Face", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

    if best_frame is None or len(best_faces) == 0:
        return "No face detected Boss. Try again with better lighting."

    cv2.imwrite(BOSS_PHOTO, best_frame)

    x, y, w, h = best_faces[0]
    embedding  = _get_embedding(best_frame, x, y, w, h)

    data = {
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "embedding":     embedding.tolist()
    }
    with open(BOSS_DATA_FILE, "w") as f:
        json.dump(data, f)

    log_info("Boss face registered!")
    speak("Your face is registered Boss! Security is now active.")
    return "Face registered Boss! Say 'security check' to verify."


def recognize_face(timeout_sec=15):
    if not os.path.exists(BOSS_DATA_FILE):
        return "Face not registered Boss. Say 'register face' first."

    try:
        with open(BOSS_DATA_FILE) as f:
            saved = json.load(f)
        saved_emb = saved.get("embedding", [])
        if not saved_emb:
            return "Face data corrupted Boss. Say 'register face' again."
    except Exception as e:
        return f"Could not load face data Boss: {e}"

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    import time
    start = time.time()

    while time.time() - start < timeout_sec:
        ret, frame = cap.read()
        if not ret:
            break

        faces, _ = _detect_faces(frame)

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                emb         = _get_embedding(frame, x, y, w, h)
                match, conf = _compare(saved_emb, emb)

                if match and conf > 55:
                    cap.release()
                    cv2.destroyAllWindows()
                    log_info(f"Boss recognized! {conf}%")
                    return f"Welcome Boss! Identity confirmed ({conf:.0f}% match)."

                color = (0, 255, 0) if match else (0, 0, 255)
                label = f"BOSS {conf:.0f}%" if match else f"Unknown {conf:.0f}%"
                cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                cv2.putText(frame, label, (x, y-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        else:
            cv2.putText(frame, "Show your face Boss...", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 165, 0), 2)

        remaining = int(timeout_sec - (time.time() - start))
        cv2.putText(frame, f"Time: {remaining}s",
                    (10, frame.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

        cv2.imshow("Cracka Security", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    return "Access denied Boss. Face not recognized."


def delete_face_data():
    deleted = []
    for f in [BOSS_PHOTO, BOSS_DATA_FILE]:
        if os.path.exists(f):
            os.remove(f)
            deleted.append(f)
    return "Face data deleted Boss." if deleted else "No face data Boss."


def get_face_status():
    if os.path.exists(BOSS_DATA_FILE):
        try:
            with open(BOSS_DATA_FILE) as f:
                data = json.load(f)
            return f"Face registered Boss! Date: {data.get('registered_at', 'unknown')}"
        except Exception:
            pass
    return "Face not registered Boss. Say 'register face'."
