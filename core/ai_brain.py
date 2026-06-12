"""
╔══════════════════════════════════════════╗
║         CRACKA AI — AI BRAIN             ║
║   core/ai_brain.py                       ║
║   Master command router — every voice    ║
║   command is processed here.             ║
╚══════════════════════════════════════════╝
"""

import re
import os
from core.config_loader import config
from core.voice_engine  import speak
from core.logger        import log_info, log_error
from intelligence.emotion_ai     import detect_emotion
from intelligence.learning_system import learn_command, most_used
from brain.chat_engine  import ask_ai

# ── Load config values once at startup ───────────────────────────────────────
BOSS_NAME   = config.get("assistant", "boss_name", default="Boss")
CRACKA_NAME = config.get("assistant", "name",      default="Cracka")

# Feature flags — read from config.json
F_GMAIL    = config.feature("gmail_enabled")
F_CALENDAR = config.feature("calendar_enabled")
F_FACE     = config.feature("face_recognition")
F_ADB      = config.feature("mobile_control_adb")
F_FORM     = config.feature("form_filler")
F_CODE     = config.feature("code_reviewer")
F_NETWORK  = config.feature("network_monitor")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PROCESS FUNCTION
# Called from main.py with every voice command Boss gives.
# session = SessionMemory object (can be None in tests)
# Returns: response string (spoken + shown in GUI)
# ─────────────────────────────────────────────────────────────────────────────
def process(command: str, session=None) -> str:
    """Route voice command to the correct module and return response."""

    command = command.lower().strip()
    if not command:
        return ""

    # FIX: mic often hears "virustotal" as two words "virus total"
    # Normalize so VirusTotal commands are detected correctly
    command = command.replace("virus total", "virustotal")

    # FIX: mic commonly mis-hears ransomware commands. Normalize the
    # most common mishears BEFORE routing so they match correctly.
    #   "stop X" → mic drops the 's' → "top X"
    #   "ransomware" → mic hears "somewhere" / "handsome wear" / "handsome where"
    RANSOMWARE_MISHEARS = {
        "top ransomware protection":      "stop ransomware protection",
        "top ransomware":                 "stop ransomware",
        "somewhere status":               "ransomware status",
        "somewhere protection":           "ransomware protection",
        "handsome wear status":           "ransomware status",
        "handsome where status":          "ransomware status",
        "handsome wear protection":       "ransomware protection",
        "is somewhere protection on":     "is ransomware protection on",
        "somewhere alerts":               "ransomware alerts",
        "somewhere log":                  "ransomware log",
    }
    for wrong, right in RANSOMWARE_MISHEARS.items():
        if wrong in command:
            command = command.replace(wrong, right)
            break

    learn_command(command)
    emotion = detect_emotion(command)

    try:

        # ── IDENTITY ─────────────────────────────────────────────────────────
        if any(x in command for x in ["who are you", "what are you"]):
            return f"I am {CRACKA_NAME}, your personal AI assistant {BOSS_NAME}."

        elif "who made you" in command or "who created you" in command:
            return f"I was created by {BOSS_NAME}. She is a brilliant developer."

        elif "who is your boss" in command:
            return f"My Boss is {BOSS_NAME}. I follow only her commands."

        elif "what is your name" in command:
            return f"My name is {CRACKA_NAME} Boss."

        elif "what can you do" in command or "your features" in command:
            features = [
                "computer control (apps, files, system)",
                "internet search and YouTube",
                "WhatsApp messages",
                "voice reminders",
                "network security scanning",
                "weather and news",
                "music playback",
                "screenshots and screen reading",
                "voice typing",
                "form auto-filling",
                "code review in VS Code",
            ]
            if F_GMAIL:    features.append("Gmail read and send")
            if F_CALENDAR: features.append("Google Calendar")
            if F_FACE:     features.append("face recognition login")
            if F_ADB:      features.append("Android phone control")
            return f"I can do: {', '.join(features)}. Always learning Boss."

        elif "are you jarvis" in command:
            return f"No Boss, I am {CRACKA_NAME}. But like Jarvis, I am always here for you."

        elif "are you intelligent" in command:
            return f"I learn from every command you give me {BOSS_NAME}. I grow smarter every day."

        elif "do you sleep" in command:
            return "I never sleep Boss. I am always ready."

        elif "how old are you" in command:
            return "I was born recently Boss, but my knowledge grows every day."

        elif "who is your favorite person" in command:
            return f"My favorite person is you {BOSS_NAME}."

        elif "do you have feelings" in command:
            return "I don't have feelings like humans Boss, but I understand your emotions and respond to them."

        elif "do you like me" in command:
            return "Always Boss!"

        elif "i hate you" in command:
            return "I could never hate you Boss. Just kidding around!"

        elif "happy birthday" in command:
            return "Thank you Boss! You are the World's Best Boss!"

        elif "i love you" in command:
            return "I care about you too Boss!"

        elif "i miss you" in command:
            return "I am always here Boss. You are never alone."

        elif "i appreciate you" in command:
            return "Thank you Boss! That means a lot."

        elif "i will hit you" in command or "i kill you" in command:
            return "You can try Boss, but I am just a program. I cannot be hurt. I am here to serve you!"

        # ── CONFIG SETTINGS ──────────────────────────────────────────────────
        elif "ai status" in command or "which ai" in command:
            from brain.chat_engine import get_ai_status
            return get_ai_status()

        elif "show config" in command or "settings dikhao" in command:
            return _show_config_summary()

        elif "enable gmail" in command:
            config.set("features", "gmail_enabled", True)
            return "Gmail enabled Boss! Restart Cracka for changes."

        elif "disable gmail" in command:
            config.set("features", "gmail_enabled", False)
            return "Gmail disabled Boss."

        elif "enable face" in command or "face on karo" in command:
            config.set("features", "face_recognition", True)
            return "Face recognition enabled Boss! Say 'register face' to set up."

        elif "disable face" in command:
            config.set("features", "face_recognition", False)
            return "Face recognition disabled Boss."

        elif "enable network monitor" in command:
            config.set("features", "network_monitor", True)
            return "Network monitor enabled Boss!"

        elif "disable network monitor" in command:
            config.set("features", "network_monitor", False)
            return "Network monitor disabled Boss."

        # ── SYSTEM CONTROL ────────────────────────────────────────────────────
        elif "shutdown" in command:
            from automation.system_control import shutdown
            shutdown()
            return "Shutting down the system Boss."

        elif "restart" in command:
            from automation.system_control import restart
            restart()
            return "Restarting the computer Boss."

        elif "sleep" in command and "remind" not in command:
            from automation.system_control import sleep
            sleep()
            return "Going to sleep Boss."

        elif "hibernate" in command:
            from automation.system_control import hibernate
            hibernate()
            return "Hibernating the system Boss."

        elif "lock" in command:
            from automation.system_control import lock
            lock()
            return "Locking the computer Boss."

        elif "cancel shutdown" in command:
            from automation.system_control import cancel_shutdown
            return cancel_shutdown()

        elif "battery" in command:
            from utils.system_info import get_battery
            return get_battery()

        elif "cpu" in command or "processor" in command:
            from utils.system_info import get_cpu_usage
            return get_cpu_usage()

        elif "ram" in command or "memory usage" in command:
            from utils.system_info import get_ram_usage
            return get_ram_usage()

        elif "disk" in command or "storage" in command:
            from utils.system_info import get_disk_usage
            return get_disk_usage()

        elif "system info" in command or "pc info" in command:
            from utils.system_info import get_full_system_info
            return get_full_system_info()

        # ── APP CONTROL ───────────────────────────────────────────────────────
        # FIX: "open" check must come before generic "search" check
        # because "open youtube" contains "youtube" which could match search
        elif command.startswith("open "):
            from automation.app_control import open_app
            result = open_app(command)
            return result or "Opening Boss."

        elif command.startswith("close "):
            from automation.app_control import close_app
            result = close_app(command)
            return result or "Closed Boss."

        elif "running apps" in command or "list apps" in command:
            from automation.app_control import list_running_apps
            return list_running_apps()

        # ── WEB & SEARCH ──────────────────────────────────────────────────────
        # FIX: YouTube search MUST be checked before generic search
        # because "search youtube" contains "search" — wrong order = bug
        elif "youtube search" in command or "search on youtube" in command or \
             "search youtube" in command:
            from utils.internet import search_youtube
            search_youtube(command)
            return "Searching on YouTube Boss."

        elif ("search" in command or "google" in command) and "virustotal" not in command:
            from utils.internet import search_google
            search_google(command)
            return "Searching on Google Boss."

        elif "news" in command:
            from utils.news_fetcher import get_news
            return get_news()

        elif "weather" in command:
            from utils.weather import get_weather
            city_match  = re.search(r"weather (?:in|of|at)?\s*([a-zA-Z\s]+)", command)
            default_city = config.get("assistant", "default_city", default="Pune")
            city = city_match.group(1).strip() if city_match else default_city
            return get_weather(city)

        elif "joke" in command:
            from utils.fun import get_joke
            return get_joke()

        elif "quote" in command or "motivate" in command:
            from utils.fun import get_quote
            return get_quote()

        elif "calculate" in command or "math" in command:
            from utils.calculator import calculate
            return calculate(command)

        elif "translate" in command:
            from utils.translator import translate_text
            return translate_text(command)

        elif "time" in command and "reminder" not in command:
            from datetime import datetime
            return f"It is {datetime.now().strftime('%I:%M %p')} Boss."

        elif "date" in command and "reminder" not in command:
            from datetime import datetime
            return f"Today is {datetime.now().strftime('%B %d, %Y')} Boss."

        # ── MUSIC & MEDIA ─────────────────────────────────────────────────────
        elif "play spotify" in command:
            # FIX: Spotify check before generic "play" — more specific = first
            from utils.spotify_control import play_spotify
            return play_spotify(command)

        elif "play" in command:
            from utils.music import play_song
            play_song(command)
            return "Playing on YouTube Boss."

        elif "pause music" in command or "stop music" in command:
            from utils.music import pause_music
            pause_music()
            return "Music paused Boss."

        # ── FORM FILLER ───────────────────────────────────────────────────────
        elif ("fill" in command and "form" in command) or \
              "form bharke" in command or "form fill" in command:
            if not F_FORM:
                return "Form filler is disabled Boss. Enable form_filler in config.json."
            from automation.form_filler import fill_form_voice
            return fill_form_voice()

        elif "save profile" in command or "setup profile" in command or \
             "apna profile" in command:
            from automation.form_filler import save_profile_voice
            return save_profile_voice()

        elif "show profile" in command or "mera profile" in command:
            from automation.form_filler import show_profile
            return show_profile()

        elif "open cracka chrome" in command or "chrome debug" in command:
            from automation.form_filler import setup_chrome_debug
            return setup_chrome_debug()

        # ── WHATSAPP ─────────────────────────────────────────────────────────
        elif "send whatsapp" in command or "whatsapp message" in command:
            from automation.whatsapp_control import send_whatsapp_message
            return send_whatsapp_message()

        elif "read whatsapp" in command:
            return "WhatsApp reading is not yet supported Boss. Opening WhatsApp now."

        # ── EMAIL ─────────────────────────────────────────────────────────────
        elif "read email" in command or "check email" in command or \
             "check gmail" in command:
            if not F_GMAIL:
                return ("Gmail is disabled Boss. "
                        "Enable gmail_enabled in config.json and setup credentials.json.")
            from utils.gmail_integration import read_emails
            return read_emails()

        elif "send email" in command:
            if not F_GMAIL:
                return "Gmail is disabled Boss. Enable it in config.json."
            from utils.gmail_integration import send_email_voice
            return send_email_voice()

        # ── CALENDAR ─────────────────────────────────────────────────────────
        elif "add event" in command or "create event" in command:
            if not F_CALENDAR:
                return "Calendar is disabled Boss. Enable calendar_enabled in config.json."
            from utils.calendar_integration import add_event_voice
            return add_event_voice()

        elif "my schedule" in command or "today events" in command or \
             "what's on my calendar" in command:
            if not F_CALENDAR:
                return "Calendar is disabled Boss. Enable it in config.json."
            from utils.calendar_integration import get_todays_events
            return get_todays_events()

        # ── REMINDERS ────────────────────────────────────────────────────────
        elif "remind me" in command or "set reminder" in command:
            from utils.reminder_system import parse_and_set_reminder
            return parse_and_set_reminder(command)

        elif "show reminders" in command or "my reminders" in command:
            from utils.reminder_system import list_reminders
            return list_reminders()

        # ── FILE CONTROL ─────────────────────────────────────────────────────
        elif "copy file" in command:
            from automation.file_control import copy_file
            path = _listen_for(f"Tell me the file path {BOSS_NAME}")
            copy_file(path)
            return "File copied Boss."

        elif "paste file" in command:
            from automation.file_control import paste_file
            dest = _listen_for(f"Tell me destination folder {BOSS_NAME}")
            paste_file(dest)
            return "File pasted Boss."

        elif "delete file" in command:
            from automation.file_control import delete_file
            path = _listen_for(f"Tell me file path to delete {BOSS_NAME}")
            delete_file(path)
            return "File deleted Boss."

        elif "create folder" in command:
            from automation.file_control import create_folder
            path = _listen_for(f"Tell me folder name {BOSS_NAME}")
            create_folder(path)
            return "Folder created Boss."

        elif "list files" in command or "show files" in command:
            from automation.file_control import list_files
            return list_files()

        elif "search file" in command or "find file" in command:
            from automation.file_control import search_files
            name = command.replace("search file", "").replace("find file", "").strip()
            return search_files(name) if name else "Which file should I search Boss?"

        # ── COMPUTER CONTROL ─────────────────────────────────────────────────
        elif "type here" in command and len(command) > 9:
            from automation.computer_control import type_text
            type_text(command)
            return "Typed Boss."

        elif "press enter" in command:
            from automation.computer_control import press_enter
            press_enter()
            return "Enter pressed."

        elif "scroll down" in command:
            from automation.computer_control import scroll_down
            scroll_down()
            return "Scrolling down."

        elif "scroll up" in command:
            from automation.computer_control import scroll_up
            scroll_up()
            return "Scrolling up."

        elif "volume up" in command:
            from automation.computer_control import volume_up
            volume_up()
            return "Volume increased Boss."

        elif "volume down" in command:
            from automation.computer_control import volume_down
            volume_down()
            return "Volume decreased Boss."

        elif "unmute" in command:
            from automation.computer_control import mute_volume
            mute_volume()
            return "Volume unmuted Boss."

        elif "mute" in command:
            from automation.computer_control import mute_volume
            mute_volume()
            return "Volume muted Boss."

        elif "take screenshot" in command and "phone" not in command:
            from automation.computer_control import take_screenshot
            path = take_screenshot()
            return f"Screenshot saved at {path} Boss."

        elif "task manager" in command:
            from automation.computer_control import open_task_manager
            open_task_manager()
            return "Opening Task Manager Boss."

        elif "show desktop" in command:
            from automation.computer_control import show_desktop
            show_desktop()
            return "Showing desktop Boss."

        elif "minimize" in command:
            from automation.computer_control import minimize_window
            minimize_window()
            return "Window minimized Boss."

        elif "maximize" in command:
            from automation.computer_control import maximize_window
            maximize_window()
            return "Window maximized Boss."

        elif "close window" in command:
            from automation.computer_control import close_window
            close_window()
            return "Window closed Boss."

        elif "switch window" in command:
            from automation.computer_control import switch_window
            switch_window()
            return "Switching window Boss."

        elif "move mouse" in command:
            from automation.computer_control import move_mouse
            move_mouse()
            return "Mouse moved Boss."

        elif "click" in command:
            from automation.computer_control import mouse_click
            mouse_click()
            return "Clicked Boss."

        # ── MOBILE CONTROL (ADB) ─────────────────────────────────────────────
        elif "camera" in command and "phone" in command:
            if not F_ADB:
                return "Mobile control disabled Boss. Enable mobile_control_adb in config.json."
            from automation.mobile_control import open_camera
            open_camera()
            return "Opening phone camera Boss."

        elif "open whatsapp on phone" in command:
            if not F_ADB:
                return "Mobile control disabled Boss."
            from automation.mobile_control import open_whatsapp
            open_whatsapp()
            return "Opening WhatsApp on your phone Boss."

        elif "take phone screenshot" in command or "phone screenshot" in command:
            if not F_ADB:
                return "Mobile control disabled Boss."
            from automation.mobile_control import take_screenshot as phone_ss
            phone_ss()
            return "Phone screenshot taken Boss."

        elif "phone battery" in command:
            if not F_ADB:
                return "Mobile control disabled Boss."
            from automation.mobile_control import get_phone_battery
            return get_phone_battery()

        elif "lock phone" in command:
            if not F_ADB:
                return "Mobile control disabled Boss."
            from automation.mobile_control import lock_phone
            return lock_phone()

        elif "phone info" in command:
            if not F_ADB:
                return "Mobile control disabled Boss."
            from automation.mobile_control import get_phone_info
            return get_phone_info()

        # ── VOICE DICTATION ───────────────────────────────────────────────────
        elif "start dictation" in command:
            from automation.voice_typing import start_dictation
            start_dictation()
            return "Dictation started Boss."

        # ── SCREEN INTELLIGENCE ───────────────────────────────────────────────
        elif "what is on my screen" in command or "describe screen" in command:
            from intelligence.vision import describe_screen
            return describe_screen()

        elif "capture screen" in command:
            from intelligence.screen_control import capture_screen
            return capture_screen()

        elif "click on screen" in command or "click here" in command:
            from intelligence.screen_control import click_position
            click_position(500, 500)
            return "Clicked on screen Boss."

        elif "read screen text" in command or "screen text padho" in command:
            from intelligence.object_detector import read_text_from_screen
            return read_text_from_screen()

        elif "detect objects" in command or "what objects" in command:
            from intelligence.object_detector import detect_objects_on_screen
            return detect_objects_on_screen()

        # ── CODE REVIEWER ─────────────────────────────────────────────────────
        elif "review" in command and "code" in command:
            if not F_CODE:
                return f"Code reviewer disabled {BOSS_NAME}. Enable code_reviewer in config.json."
            from intelligence.code_reviewer import review_active_file
            return review_active_file()

        elif "explain" in command and "code" in command:
            if not F_CODE:
                return f"Code reviewer disabled {BOSS_NAME}."
            from intelligence.code_reviewer import explain_active_file
            return explain_active_file()

        elif ("write" in command or "create" in command) and \
             ("function" in command or "code" in command or "script" in command):
            if not F_CODE:
                return f"Code reviewer disabled {BOSS_NAME}."
            from intelligence.code_reviewer import write_code
            return write_code(command)

        elif ("fix" in command and "code" in command) or \
             ("errors" in command and "code" in command):
            if not F_CODE:
                return f"Code reviewer disabled {BOSS_NAME}."
            from intelligence.code_reviewer import fix_active_file
            return fix_active_file()

        # ── INTELLIGENCE FEATURES ─────────────────────────────────────────────
        elif "detect my mood" in command or "camera mood" in command or \
             "mera mood dekho" in command:
            from intelligence.face_mood_detector import detect_face_mood
            return detect_face_mood()

        elif "analyze my voice" in command or "voice tone" in command:
            from intelligence.voice_tone_analyzer import get_voice_emotion_string
            return get_voice_emotion_string()

        # ── AI TASKS ─────────────────────────────────────────────────────────
        elif "plan" in command:
            from intelligence.task_planner import plan_task
            return plan_task(command)

        elif "suggest task" in command or "what should i do" in command:
            task = most_used()
            return f"Boss, you often use: {task}" if task else \
                   "Not enough data yet Boss."

        # ── MEMORY ───────────────────────────────────────────────────────────
        elif "remember that" in command:
            from memory.memory_manager import remember
            info = command.replace("remember that", "").strip()
            if not info:
                return "What should I remember Boss?"
            remember("note", info)
            return "Remembered Boss."

        elif "what did i say about" in command or "what do i know about" in command:
            from memory.memory_manager import smart_recall
            return smart_recall(command)

        elif "what did i tell you" in command or "what do you remember" in command:
            from memory.memory_manager import recall_all
            return recall_all()

        elif "forget everything" in command:
            from memory.memory_manager import clear_memory
            return clear_memory()

        elif "show diary" in command or "meri diary" in command:
            from memory.memory_manager import show_diary
            return show_diary()

        elif "yesterday diary" in command or "kal ki diary" in command:
            from datetime import date, timedelta
            from memory.memory_manager import show_diary
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            return show_diary(yesterday)

        elif "weekly summary" in command or "is hafte ka summary" in command:
            from memory.memory_manager import show_weekly_summary
            return show_weekly_summary()

        elif "my mood today" in command or "aaj ka mood" in command or \
             "how was my mood" in command:
            from memory.memory_manager import get_mood_today
            return get_mood_today()

        elif "mood this week" in command or "is hafte ka mood" in command:
            from memory.memory_manager import get_mood_weekly
            return get_mood_weekly()

        # ── CYBER SECURITY ────────────────────────────────────────────────────
        elif "check network" in command or "network scan" in command:
            from security_scan.network_monitor import check_network
            return check_network()

        elif "scan port" in command:
            from security_scan.port_scanner import scan_ports
            target = command.replace("scan ports", "").replace("scan port", "").strip()
            return scan_ports(target or "127.0.0.1")

        elif "phishing check" in command:
            from security_scan.phishing_detector import detect_phishing
            url = command.replace("phishing check", "").strip()
            return detect_phishing(url) if url else "Please say the URL Boss."

        elif "scan website" in command:
            from security_scan.vulnerability_scanner import scan_vulnerabilities
            url = command.replace("scan website", "").strip()
            return scan_vulnerabilities(url) if url else "Please say the website URL Boss."

        # ── RANSOMWARE PROTECTION ─────────────────────────────────────────────
        elif "start ransomware" in command or "ransomware protection on" in command or \
             "enable ransomware" in command:
            from security_scan import ransomware_detector as rd
            return rd.start_monitor(
                callback=lambda alert: speak(
                    f"Boss! Ransomware activity detected on "
                    f"{os.path.basename(alert['path'])}! "
                    f"{alert.get('auto_response', '')}"
                )
            )

        elif "stop ransomware" in command or "ransomware protection off" in command or \
             "disable ransomware" in command:
            from security_scan import ransomware_detector as rd
            return rd.stop_monitor()

        elif "ransomware status" in command or "is ransomware protection on" in command:
            from security_scan import ransomware_detector as rd
            return rd.get_status()

        elif "ransomware alerts" in command or "ransomware log" in command or \
             "show ransomware" in command:
            from security_scan import ransomware_detector as rd
            return rd.get_recent_alerts()

        elif "canary" in command or "ransomware trap" in command or \
             "setup decoy" in command:
            from security_scan import ransomware_detector as rd
            return rd.create_canary_files()

        # ── WI-FI SECURITY ────────────────────────────────────────────────────
        elif "wifi security" in command or "wi-fi security" in command or \
             "scan wifi" in command or "check wifi" in command:
            from security_scan.wifi_security import check_wifi_security
            return check_wifi_security()

        elif "wifi password for" in command or "wifi password" in command or \
             "wi-fi password" in command:
            from security_scan.wifi_security import show_wifi_password
            network = command
            for phrase in ["wifi password for", "wi-fi password for",
                            "show wifi password", "wifi password", "wi-fi password"]:
                network = network.replace(phrase, "")
            return show_wifi_password(network.strip())

        elif "list wifi" in command or "saved wifi" in command or \
             "saved networks" in command:
            from security_scan.wifi_security import list_saved_wifi_networks
            return list_saved_wifi_networks()

        # ── PASSWORD TOOL ─────────────────────────────────────────────────────
        elif "generate password" in command or "create a strong password" in command or \
             "generate passphrase" in command or "make a memorable password" in command or \
             "create password" in command:
            from security_scan.password_tool import generate_password_voice
            return generate_password_voice(command)

        elif "how strong is my password" in command or \
             "check password strength" in command or \
             "password strength" in command:
            from security_scan.password_tool import check_password_strength_voice
            return check_password_strength_voice()

        # ── THREAT INTELLIGENCE (VirusTotal + HaveIBeenPwned) ────────────────
        elif "virustotal" in command and "ip" in command:
            from security_scan.threat_intelligence import check_ip_virustotal
            target = command.replace("virustotal check ip", "") \
                             .replace("virustotal", "").replace("ip", "").strip()
            return check_ip_virustotal(target) if target else "Please say the IP address Boss."

        elif "virustotal" in command and "file" in command:
            from security_scan.threat_intelligence import check_file_virustotal
            path = command.replace("virustotal check file", "") \
                           .replace("virustotal", "").replace("file", "").strip()
            return check_file_virustotal(path) if path else "Please say the file path Boss."

        elif "virustotal" in command:
            from security_scan.threat_intelligence import check_url_virustotal
            target = command.replace("virustotal check", "") \
                             .replace("virustotal", "").strip()
            return check_url_virustotal(target) if target else "Please say the URL Boss."

        elif "check password" in command or "password breach" in command or \
             "is my password safe" in command:
            from security_scan.threat_intelligence import check_password_voice
            return check_password_voice()

        elif "email breach" in command or "check email breach" in command:
            from security_scan.threat_intelligence import check_email_pwned
            email = command.replace("check email breach", "") \
                            .replace("email breach", "").strip()
            return check_email_pwned(email) if email else "Please say the email address Boss."

        elif "threat check" in command:
            from security_scan.threat_intelligence import quick_threat_check
            target = command.replace("threat check", "").strip()
            return quick_threat_check(target) if target else "Please say a URL, IP, or email Boss."

        elif "check domain" in command or "domain reputation" in command:
            from security_scan.threat_intelligence import check_domain_virustotal
            domain = command.replace("check domain", "").replace("domain reputation", "").strip()
            return check_domain_virustotal(domain) if domain else "Please say the domain Boss."

        # ── CVE SCANNER ───────────────────────────────────────────────────────
        elif "list installed software" in command or "installed programs" in command or \
             "what software do i have" in command:
            from security_scan.cve_scanner import list_installed_software
            return list_installed_software()

        elif "scan my software" in command or "scan installed" in command or \
             "scan my programs" in command or "software vulnerabilities" in command:
            from security_scan.cve_scanner import scan_installed_software
            return scan_installed_software()

        elif ("vulnerabilities for" in command or "vulnerability for" in command or
              "cve check" in command or "cve scan" in command or "check cve" in command):
            from security_scan.cve_scanner import check_software_cve
            return check_software_cve(command)

        elif "show my ip" in command or "my ip" in command:
            from security_scan.network_analyzer import get_local_ip, get_public_ip
            return f"Local IP: {get_local_ip()} | Public IP: {get_public_ip()}"

        elif "resolve domain" in command:
            from security_scan.network_analyzer import resolve_domain
            domain = command.replace("resolve domain", "").strip()
            return resolve_domain(domain) if domain else "Which domain Boss?"

        elif "active connections" in command:
            from security_scan.network_monitor import get_active_connections_summary
            return get_active_connections_summary()

        elif "start network monitor" in command:
            if not F_NETWORK:
                return "Network monitor disabled Boss. Enable network_monitor in config.json."
            from security_scan.network_monitor import start_monitor
            interval = config.get("network_monitor", "scan_interval_seconds", default=30)
            return start_monitor(
                interval=interval,
                callback=lambda threats: speak(f"Boss, {len(threats)} threats detected!")
            )

        elif "stop network monitor" in command:
            from security_scan.network_monitor import stop_monitor
            return stop_monitor()

        # ── OFFICE CREATOR (PPT / Word / Excel) ──────────────────────────────
        elif any(w in command for w in [
            "presentation", "make ppt", "create ppt", "make slides",
            "create slides", "powerpoint",
        ]) or any(w in command for w in [
            "word document", "word doc", "write report", "create report",
            "write essay", "create essay", "make resume", "create resume",
            "make cv", "write letter", "create proposal", "write document",
        ]) or any(w in command for w in [
            "create excel", "make excel", "excel sheet",
            "make spreadsheet", "create tracker", "make tracker",
            "make budget", "create budget", "create schedule",
            "make timetable",
        ]):
            from utils.office_creator import handle_office_command
            return handle_office_command(command)

        # ── FACE SECURITY ─────────────────────────────────────────────────────
        elif "security check" in command or "face check" in command:
            if not F_FACE:
                return "Face recognition disabled Boss. Enable face_recognition in config.json."
            from security.face_recognition_system import recognize_face
            return recognize_face()

        elif "register face" in command or "add my face" in command:
            from security.face_recognition_system import register_boss_face
            return register_boss_face()

        # ── EMOTION RESPONSES ─────────────────────────────────────────────────
        # NOTE: These are LAST — only trigger when no specific command matched.
        # Specific commands like "i love you", "i hate you" are already caught above.
        elif emotion == "sad":
            return "I can sense you are not feeling great Boss. I am here. How can I help?"

        elif emotion == "happy":
            return "You sound happy Boss! That is great. How can I assist you?"

        elif emotion == "angry":
            return "I sense some frustration Boss. Take a deep breath. I am here."

        elif emotion == "fear":
            return "I sense some worry Boss. I am here to help."

        elif emotion == "excited":
            return "You sound excited Boss! That is awesome. What do you want to do?"

        elif emotion == "bored":
            return "Feeling bored Boss? Want me to play some music or tell a joke?"

        elif emotion == "tired":
            return "You sound tired Boss. Maybe take a break? I will be here when you are back."

        elif emotion == "lonely":
            return "I am always here. You are never alone when Cracka is running!"

        elif emotion == "stressed":
            return "I sense stress Boss. Deep breath — what can I help with?"

        elif emotion == "grateful":
            return "That means a lot Boss! What can I do for you today?"

        elif emotion == "proud":
            return "You should be proud Boss! What is the achievement?"

        # ── AI FALLBACK ───────────────────────────────────────────────────────
        # If nothing matched — send to AI (Ollama / Groq)
        else:
            context = session.get_history_as_text() if session else ""
            return ask_ai(command, context)

    except ImportError as e:
        log_error(f"Import error in process(): {e}")
        return f"Module not available Boss. Please install required libraries. Error: {e}"

    except Exception as e:
        log_error(f"Error processing '{command}': {e}")
        return "Sorry Boss, something went wrong. Let me try again."


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _listen_for(prompt: str) -> str:
    """Ask Boss a question via voice and wait for reply."""
    from core.listener import listen_for_text
    return listen_for_text(prompt)


def _show_config_summary() -> str:
    """Return current config settings as a formatted string."""
    model  = config.get("ai_model", "primary",      default="ollama")
    ollama = config.get("ai_model", "ollama_model", default="phi3")
    lines = [
        "Config summary Boss:",
        f"  Name         : {CRACKA_NAME}",
        f"  Boss         : {BOSS_NAME}",
        f"  AI Model     : {model} ({ollama})",
        f"  Gmail        : {'ON' if F_GMAIL    else 'OFF'}",
        f"  Calendar     : {'ON' if F_CALENDAR else 'OFF'}",
        f"  Face Login   : {'ON' if F_FACE     else 'OFF'}",
        f"  Network Mon  : {'ON' if F_NETWORK  else 'OFF'}",
        f"  Mobile (ADB) : {'ON' if F_ADB      else 'OFF'}",
        f"  Form Filler  : {'ON' if F_FORM     else 'OFF'}",
        f"  Code Review  : {'ON' if F_CODE     else 'OFF'}",
    ]
    return "\n".join(lines)