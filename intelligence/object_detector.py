"""
intelligence/object_detector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Screen ya camera se objects pehchano.
Uses: YOLOv8 (ultralytics) + OpenCV
"""

import cv2
import os
from core.logger import log_info, log_error


def detect_objects_on_screen() -> str:
    """
    Screenshot lo aur objects detect karo using YOLO.
    """
    try:
        from ultralytics import YOLO
        import pyautogui
        from PIL import Image
        import numpy as np

        # Screenshot lo
        os.makedirs("data", exist_ok=True)
        screenshot = pyautogui.screenshot()
        img_path   = "data/screen_detect.png"
        screenshot.save(img_path)

        return _run_yolo(img_path, source="screen")

    except ImportError:
        return _detect_with_ollama_vision("screen")
    except Exception as e:
        log_error(f"Object detection error: {e}")
        return f"Detection failed Boss: {e}"


def detect_objects_from_camera() -> str:
    """Camera se objects detect karo."""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return "Camera not available Boss."

        import time
        time.sleep(1)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return "Could not capture frame Boss."

        os.makedirs("data", exist_ok=True)
        img_path = "data/camera_detect.jpg"
        cv2.imwrite(img_path, frame)

        return _run_yolo(img_path, source="camera")

    except ImportError:
        return _detect_with_ollama_vision("camera")
    except Exception as e:
        log_error(f"Camera detection error: {e}")
        return f"Detection failed Boss: {e}"


def _run_yolo(img_path: str, source: str = "screen") -> str:
    """Run YOLOv8 detection on an image."""
    try:
        from ultralytics import YOLO
        import numpy as np

        # Load model (auto-downloads on first run)
        model   = YOLO("yolov8n.pt")
        results = model(img_path, verbose=False)

        if not results or not results[0].boxes:
            return f"No objects detected on {source} Boss."

        # Extract detected objects
        objects  = {}
        for box in results[0].boxes:
            class_id   = int(box.cls[0])
            class_name = model.names[class_id]
            confidence = float(box.conf[0])
            if confidence > 0.4:
                objects[class_name] = objects.get(class_name, 0) + 1

        if not objects:
            return f"No clear objects detected on {source} Boss."

        obj_list = [f"{name} ({count}x)" if count > 1 else name
                    for name, count in objects.items()]

        log_info(f"Objects detected on {source}: {obj_list}")

        result = f"I can see on {source} Boss: {', '.join(obj_list)}."

        # Save annotated image
        annotated = results[0].plot()
        ann_path  = f"data/{source}_detected.jpg"
        cv2.imwrite(ann_path, annotated)
        result += f" Annotated image saved at {ann_path}."

        # Cleanup original
        if os.path.exists(img_path):
            os.remove(img_path)

        return result

    except Exception as e:
        log_error(f"YOLO error: {e}")
        return _detect_with_ollama_vision(source, img_path)


def _detect_with_ollama_vision(source: str, img_path: str = None) -> str:
    """Fallback: Use Ollama LLaVA for object detection."""
    try:
        import ollama

        if not img_path:
            if source == "screen":
                import pyautogui
                screenshot = pyautogui.screenshot()
                img_path   = "data/screen_detect.png"
                screenshot.save(img_path)
            else:
                return "No image available for detection Boss."

        response = ollama.chat(
            model="llava",
            messages=[{
                "role":    "user",
                "content": "List all objects you can see in this image. Be specific and concise.",
                "images":  [img_path]
            }]
        )

        result = response["message"]["content"].strip()
        log_info(f"LLaVA detected objects on {source}")
        return f"Objects on {source} Boss: {result}"

    except Exception as e:
        log_error(f"LLaVA detection error: {e}")
        return (f"Object detection not available Boss. "
                f"Install: pip install ultralytics")


def read_text_from_screen() -> str:
    """OCR — screen par jo text hai woh padho."""
    try:
        import pytesseract
        import pyautogui
        from PIL import Image

        screenshot = pyautogui.screenshot()
        text       = pytesseract.image_to_string(screenshot)
        text       = text.strip()

        if not text:
            return "No readable text found on screen Boss."

        # Return first 300 chars
        if len(text) > 300:
            text = text[:300] + "..."

        return f"Text on screen Boss: {text}"

    except ImportError:
        return "pytesseract not installed Boss. Run: pip install pytesseract"
    except Exception as e:
        log_error(f"OCR error: {e}")
        return f"Could not read screen text Boss: {e}"