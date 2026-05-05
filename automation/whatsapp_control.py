"""
automation/whatsapp_control.py
Send WhatsApp messages via desktop app using voice input.
"""

import pyautogui
import time
import os
from core.logger import log_info, log_error


def send_whatsapp_message() -> str:
    """Send a WhatsApp message using voice for contact and message."""
    from core.listener import listen_for_text
    from core.voice_engine import speak

    # Get contact name by voice
    contact = listen_for_text("Which contact should I message Boss?")
    if not contact:
        return "Could not understand the contact name Boss."

    # Get message by voice
    message = listen_for_text("What should I say Boss?")
    if not message:
        return "Could not understand the message Boss."

    try:
        # Open WhatsApp Desktop
        os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        time.sleep(6)

        # Search for contact
        pyautogui.hotkey("ctrl", "f")
        time.sleep(0.8)
        pyautogui.write(contact, interval=0.05)
        time.sleep(2)
        pyautogui.press("enter")
        time.sleep(1)

        # Type and send message
        pyautogui.write(message, interval=0.04)
        pyautogui.press("enter")

        log_info(f"WhatsApp message sent to {contact}")
        return f"Message sent to {contact} Boss."

    except Exception as e:
        log_error(f"WhatsApp error: {e}")
        return f"Could not send WhatsApp message Boss. Error: {e}"


def send_whatsapp_web(contact: str, message: str) -> str:
    """Send WhatsApp message via WhatsApp Web (no desktop app needed)."""
    import webbrowser
    import urllib.parse
    encoded = urllib.parse.quote(message)
    url = f"https://web.whatsapp.com/send?phone={contact}&text={encoded}"
    webbrowser.open(url)
    time.sleep(5)
    pyautogui.press("enter")
    return f"Message sent via WhatsApp Web Boss."