"""
security/face_recognition_system.py
Face recognition for Boss authentication.
Uses face_recognition + OpenCV.
"""

import cv2
import face_recognition
import os
import numpy as np
from core.logger import log_info, log_error

BOSS_PHOTO = "data/boss.jpg"
KNOWN_FACES_DIR = "data/known_faces"


def register_boss_face() -> str:
    """
    Capture Boss's face from webcam and save it.
    Run this once to set up face recognition.
    """
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    os.makedirs("data", exist_ok=True)
    from core.voice_engine import speak
    speak("Look at the camera Boss. I'll capture your face in 3 seconds.")

    import time
    time.sleep(3)

    ret, frame = cap.read()
    cap.release()

    if not ret:
        return "Could not capture image Boss."

    # Check if a face is in the photo
    rgb = frame[:, :, ::-1]
    encodings = face_recognition.face_encodings(rgb)
    if not encodings:
        return "No face detected in frame Boss. Please try again with better lighting."

    cv2.imwrite(BOSS_PHOTO, frame)
    log_info("Boss face registered successfully")
    return "Your face has been registered Boss. Security is active."


def recognize_face(timeout_sec: int = 15) -> str:
    """
    Attempt to recognize Boss's face from webcam.
    Returns welcome message or unknown person.
    """
    if not os.path.exists(BOSS_PHOTO):
        return "Boss face not registered yet. Please say 'register face' first Boss."

    try:
        boss_image = face_recognition.load_image_file(BOSS_PHOTO)
        boss_encodings = face_recognition.face_encodings(boss_image)
        if not boss_encodings:
            return "Boss photo does not have a detectable face. Please re-register Boss."
        boss_encoding = boss_encodings[0]
    except Exception as e:
        log_error(f"Face load error: {e}")
        return "Error loading boss face data Boss."

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera not available Boss."

    import time
    start = time.time()

    while time.time() - start < timeout_sec:
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for faster processing
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb = small[:, :, ::-1]

        locations = face_recognition.face_locations(rgb)
        encodings = face_recognition.face_encodings(rgb, locations)

        for encoding in encodings:
            results = face_recognition.compare_faces([boss_encoding], encoding, tolerance=0.5)
            distance = face_recognition.face_distance([boss_encoding], encoding)[0]

            if results[0]:
                cap.release()
                cv2.destroyAllWindows()
                confidence = round((1 - distance) * 100, 1)
                log_info(f"Boss recognized with {confidence}% confidence")
                return f"Welcome Boss! Identity confirmed ({confidence}% confidence)."

        # Draw face boxes
        for (top, right, bottom, left) in locations:
            top *= 2; right *= 2; bottom *= 2; left *= 2
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 255), 2)

        cv2.putText(frame, "Scanning...", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imshow("Cracka Security", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    log_error("Unknown person detected or timeout")
    return "Access denied. Unknown person detected Boss."