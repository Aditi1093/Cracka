"""
automation/mobile_control.py
Android phone control via ADB (USB debugging).
Requirements: ADB installed, USB debugging enabled on phone.
"""

import subprocess
import os
from core.logger import log_info, log_error


def _adb(command: str) -> str:
    """Run an ADB command and return output."""
    try:
        result = subprocess.run(
            f"adb {command}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "ADB command timed out"
    except Exception as e:
        log_error(f"ADB error: {e}")
        return f"ADB error: {e}"


def check_adb_connected() -> bool:
    """Check if a device is connected via ADB."""
    output = _adb("devices")
    return "device" in output and len(output.strip().split("\n")) > 1


def open_camera():
    _adb("shell am start -a android.media.action.IMAGE_CAPTURE")
    log_info("Phone camera opened")


def open_whatsapp():
    _adb("shell monkey -p com.whatsapp -c android.intent.category.LAUNCHER 1")
    log_info("WhatsApp opened on phone")


def open_app_on_phone(package: str):
    """Open any app by package name."""
    _adb(f"shell monkey -p {package} -c android.intent.category.LAUNCHER 1")


def take_screenshot() -> str:
    """Take screenshot on phone and pull to PC."""
    _adb("shell screencap /sdcard/phone_screen.png")
    _adb("pull /sdcard/phone_screen.png data/phone_screen.png")
    log_info("Phone screenshot taken")
    return "data/phone_screen.png"


def get_phone_battery() -> str:
    """Get phone battery level."""
    output = _adb("shell dumpsys battery | grep level")
    if output:
        level = output.strip().split(":")[1].strip()
        return f"Phone battery is at {level}% Boss."
    return "Could not read phone battery Boss."


def lock_phone():
    _adb("shell input keyevent 26")  # Power button
    return "Phone locked Boss."


def unlock_phone():
    _adb("shell input keyevent 82")  # Menu key (unlock)


def send_sms(number: str, message: str):
    """Send SMS via ADB."""
    _adb(f'shell am start -a android.intent.action.SENDTO -d sms:{number} --es sms_body "{message}" --ez exit_on_sent true')


def get_phone_info() -> str:
    """Get phone model and Android version."""
    model = _adb("shell getprop ro.product.model")
    version = _adb("shell getprop ro.build.version.release")
    return f"Phone: {model}, Android {version} Boss."


def install_apk(apk_path: str) -> str:
    """Install an APK file."""
    result = _adb(f"install {apk_path}")
    if "Success" in result:
        return "App installed successfully Boss."
    return f"Installation failed: {result}"