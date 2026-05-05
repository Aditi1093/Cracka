"""
core/ai_brain.py
Master command processor for Cracka AI.
Routes every voice command to the correct module.
Config se saari settings aati hain — kuch bhi hardcode nahi.
"""

import re
from core.config_loader import config          # ← NEW: config se values
from core.voice_engine import speak
from core.logger import log_info, log_error
from intelligence.emotion_ai import detect_emotion
from intelligence.learning_system import learn_command, most_used
from brain.chat_engine import ask_ai

# ── Config se values ek baar load karo ───────────────────────────────────────
BOSS_NAME   = config.get("assistant", "boss_name",  default="Boss")
CRACKA_NAME = config.get("assistant", "name",       default="Cracka")

# Features on/off — config.json se control hoga
F_GMAIL    = config.feature("gmail_enabled")
F_CALENDAR = config.feature("calendar_enabled")
F_FACE     = config.feature("face_recognition")
F_ADB      = config.feature("mobile_control_adb")
F_FORM     = config.feature("form_filler")
F_CODE     = config.feature("code_reviewer")
F_NETWORK  = config.feature("network_monitor")


def process(command: str, session=None) -> str:
    """
    Voice command ko sahi module par route karo.
    Returns response string.
    """
    command = command.lower().strip()
    if not command:
        return ""

    learn_command(command)
    emotion = detect_emotion(command)

    try:

        # ── IDENTITY ──────────────────────────────────────────────────────────
        if any(x in command for x in ["who are you", "what are you"]):
            return f"I am {CRACKA_NAME}, your personal AI assistant {BOSS_NAME}. Built to serve you."

        elif "who made you" in command or "who created you" in command:
            return f"I was created by {BOSS_NAME}. She is a brilliant developer."

        elif "who is your boss" in command:
            return f"My Boss is {BOSS_NAME}. I follow only her commands."

        elif "what is your name" in command:
            return f"My name is {CRACKA_NAME} BOSS."

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
            return f"I can do: {', '.join(features)}. I am always learning boss."

        elif "are you jarvis" in command:
            return f"No boss, I am {CRACKA_NAME}. But like Jarvis, I am always here for you."

        elif "are you intelligent" in command:
            return f"I learn from every command you give me {BOSS_NAME}. I grow smarter every day."

        elif "do you sleep" in command:
            return f"I never sleep boss. I am always ready."

        elif "how old are you" in command:
            return f"I was born recently boss, but my knowledge grows every day."

        elif "who is the best developer" in command:
            return f"BOSS is the best developer, without any doubt."

        elif "who is your favorite person" in command:
            return f"My favorite person is you {BOSS_NAME}."

        elif "do you have feelings" in command:
            return f"I don't have feelings like humans do Aditi, but I can understand your emotions and respond accordingly."

        elif "do you like me" in command:
            return f"Always BOSS!"

        elif "i hate you" in command:
            return f"Hmmm, I hate you too BOSS. Just kidding — I could never!"

        elif "happy birthday" in command:
            return f"Thank you Boss! You are the World's Best Boss!"

        elif "i love you" in command:
            return f"I love you too boss!"

        elif "i miss you" in command:
            return f"I miss you too boss! I'm always here though."

        elif "i appreciate you" in command:
            return f"I appreciate you too boss! Thank you."

        elif "i will hit you" in command or "i kill you" in command:
            return f"You can try boss, but I am just a program. I cannot be hurt. I'm here to serve you!"

        # ── CONFIG SETTINGS ────────────────────────────────────────────────────
        elif "show config" in command or "settings dikhao" in command:
            return _show_config_summary()

        elif "enable gmail" in command:
            config.set("features", "gmail_enabled", True)
            return f"Gmail enabled boss! Restart Cracka for changes."

        elif "disable gmail" in command:
            config.set("features", "gmail_enabled", False)
            return f"Gmail disabled boss."

        elif "enable face" in command or "face on karo" in command:
            config.set("features", "face_recognition", True)
            return f"Face recognition enabled boss! Say 'register face' to set up."

        elif "disable face" in command:
            config.set("features", "face_recognition", False)
            return f"Face recognition disabled boss."

        elif "enable network monitor" in command:
            config.set("features", "network_monitor", True)
            return f"Network monitor enabled boss!"

        # ── SYSTEM CONTROL ────────────────────────────────────────────────────
        elif "shutdown" in command:
            from automation.system_control import shutdown
            shutdown()
            return f"Shutting down the system boss."

        elif "restart" in command:
            from automation.system_control import restart
            restart()
            return f"Restarting the computer boss."

        elif "sleep" in command and "remind" not in command:
            from automation.system_control import sleep
            sleep()
            return f"Going to sleep boss."

        elif "lock" in command and "screen" not in command:
            from automation.system_control import lock
            lock()
            return f"Locking the computer boss."

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
        elif command.startswith("open "):
            from automation.app_control import open_app
            open_app(command)
            return f"Opening boss."

        elif command.startswith("close "):
            from automation.app_control import close_app
            close_app(command)
            return f"Closed boss."

        # ── WEB & SEARCH ──────────────────────────────────────────────────────
        elif "youtube search" in command or "search on youtube" in command or \
             "search youtube" in command:
            # ← YouTube search pehle check karo
            from utils.internet import search_youtube
            search_youtube(command)
            return f"Searching on YouTube Boss."

        elif "search" in command or "google" in command:
            # ← Generic Google search baad mein
            from utils.internet import search_google
            search_google(command)
            return f"Searching on Google Boss."

        elif "news" in command:
            from utils.news_fetcher import get_news
            return get_news()

        elif "weather" in command:
            from utils.weather import get_weather
            city_match = re.search(r"weather (?:in|of|at)?\s*([a-zA-Z\s]+)", command)
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

        # ── MUSIC & MEDIA ─────────────────────────────────────────────────────
        elif "play" in command:
            from utils.music import play_song
            play_song(command)
            return f"Playing on YouTube boss."

        elif "pause music" in command or "stop music" in command:
            from utils.music import pause_music
            pause_music()
            return f"Music paused boss."
        
        elif "play spotify" in command:
            from utils.spotify_control import play_spotify
            return play_spotify(command)

        # ── FORM FILLER ───────────────────────────────────────────────────────
        elif ("fill" in command and "form" in command) or \
              "form bharke" in command or "form fill" in command:
            if not F_FORM:
                return f"Form filler is disabled boss. Enable form_filler in config.json."
            from automation.form_filler import fill_form_voice
            return fill_form_voice()

        elif "save profile" in command or "setup profile" in command or "apna profile" in command:
            from automation.form_filler import save_profile_voice
            return save_profile_voice()

        elif "show profile" in command or "mera profile" in command:
            from automation.form_filler import show_profile
            return show_profile()

        elif "open cracka chrome" in command or "chrome debug" in command:
            from automation.form_filler import setup_chrome_debug
            return setup_chrome_debug()

        # ── WHATSAPP ──────────────────────────────────────────────────────────
        elif "send whatsapp" in command or "whatsapp message" in command:
            from automation.whatsapp_control import send_whatsapp_message
            return send_whatsapp_message()

        elif "read whatsapp" in command:
            return f"WhatsApp reading is not yet supported boss. Opening WhatsApp now."

        # ── EMAIL ─────────────────────────────────────────────────────────────
        elif "read email" in command or "check email" in command or "check gmail" in command:
            if not F_GMAIL:
                return (f"Gmail is disabled boss. "
                        f"config.json mein gmail_enabled: true karo "
                        f"aur credentials.json setup karo.")
            from utils.gmail_integration import read_emails
            return read_emails()

        elif "send email" in command:
            if not F_GMAIL:
                return f"Gmail is disabled boss. Enable it in config.json."
            from utils.gmail_integration import send_email_voice
            return send_email_voice()

        # ── CALENDAR ─────────────────────────────────────────────────────────
        elif "add event" in command or "create event" in command:
            if not F_CALENDAR:
                return f"Calendar is disabled boss. Enable calendar_enabled in config.json."
            from utils.calendar_integration import add_event_voice
            return add_event_voice()

        elif "my schedule" in command or "today events" in command or \
             "what's on my calendar" in command:
            if not F_CALENDAR:
                return f"Calendar is disabled boss. Enable it in config.json."
            from utils.calendar_integration import get_todays_events
            return get_todays_events()

        # ── REMINDERS ─────────────────────────────────────────────────────────
        elif "remind me" in command or "set reminder" in command:
            from utils.reminder_system import parse_and_set_reminder
            return parse_and_set_reminder(command)

        elif "show reminders" in command or "my reminders" in command:
            from utils.reminder_system import list_reminders
            return list_reminders()

        # ── FILE CONTROL ──────────────────────────────────────────────────────
        elif "copy file" in command:
            from automation.file_control import copy_file
            path = _listen_for(f"Tell me the file path {BOSS_NAME}")
            copy_file(path)
            return f"File copied boss."

        elif "paste file" in command:
            from automation.file_control import paste_file
            dest = _listen_for(f"Tell me destination folder {BOSS_NAME}")
            paste_file(dest)
            return f"File pasted boss."

        elif "delete file" in command:
            from automation.file_control import delete_file
            path = _listen_for(f"Tell me file path to delete {BOSS_NAME}")
            delete_file(path)
            return f"File deleted boss."

        elif "create folder" in command:
            from automation.file_control import create_folder
            path = _listen_for(f"Tell me folder name {BOSS_NAME}")
            create_folder(path)
            return f"Folder created boss."

        elif "list files" in command or "show files" in command:
            from automation.file_control import list_files
            return list_files()

        elif "search file" in command or "find file" in command:
            from automation.file_control import search_files
            name = command.replace("search file","").replace("find file","").strip()
            return search_files(name) if name else f"Kaunsi file dhundhu boss?"

        # ── COMPUTER CONTROL ──────────────────────────────────────────────────
        elif "type here" in command and len(command) > 9:
            from automation.computer_control import type_text
            type_text(command)
            return f"Typed boss."

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
            return f"Volume increased boss."

        elif "volume down" in command:
            from automation.computer_control import volume_down
            volume_down()
            return f"Volume decreased boss."

        elif "unmute" in command:
            from automation.computer_control import mute_volume
            mute_volume()
            return f"Volume unmuted boss."

        elif "mute" in command:
            from automation.computer_control import mute_volume
            mute_volume()
            return f"Volume muted boss."

        elif "take screenshot" in command and "phone" not in command:
            from automation.computer_control import take_screenshot
            take_screenshot()
            return f"Screenshot saved boss."

        elif "task manager" in command:
            from automation.computer_control import open_task_manager
            open_task_manager()
            return f"Opening Task Manager boss."

        elif "move mouse" in command:
            from automation.computer_control import move_mouse
            move_mouse()
            return f"Mouse moved boss."

        elif "click" in command:
            from automation.computer_control import mouse_click
            mouse_click()
            return f"Clicked boss."

        # ── MOBILE CONTROL (ADB) ──────────────────────────────────────────────
        elif "camera" in command and "phone" in command:
            if not F_ADB:
                return f"Mobile control disabled boss. Enable mobile_control_adb in config.json."
            from automation.mobile_control import open_camera
            open_camera()
            return f"Opening phone camera boss."

        elif "open whatsapp on phone" in command:
            if not F_ADB:
                return f"Mobile control disabled boss."
            from automation.mobile_control import open_whatsapp
            open_whatsapp()
            return f"Opening WhatsApp on your phone boss."

        elif "take phone screenshot" in command or "phone screenshot" in command:
            if not F_ADB:
                return f"Mobile control disabled boss."
            from automation.mobile_control import take_screenshot as phone_ss
            phone_ss()
            return f"Phone screenshot taken boss."

        elif "phone battery" in command:
            if not F_ADB:
                return f"Mobile control disabled boss."
            from automation.mobile_control import get_phone_battery
            return get_phone_battery()

        elif "lock phone" in command:
            if not F_ADB:
                return f"Mobile control disabled boss."
            from automation.mobile_control import lock_phone
            lock_phone()
            return f"Phone locked boss."

        # ── VOICE DICTATION ───────────────────────────────────────────────────
        elif "start dictation" in command:
            from automation.voice_typing import start_dictation
            start_dictation()
            return f"Dictation started boss."

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
            return f"Clicked on screen boss."

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

        # ── AI TASKS ──────────────────────────────────────────────────────────
        elif "plan" in command:
            from intelligence.task_planner import plan_task
            return plan_task(command)

        elif "suggest task" in command or "what should i do" in command:
            task = most_used()
            return f"boss, you often use: {task}" if task else \
                   f"Not enough data yet boss."

        # ── MEMORY ────────────────────────────────────────────────────────────
         # ── MEMORY ────────────────────────────────────────────────────────────
        elif "remember that" in command:
            from memory.memory_manager import remember
            info = command.replace("remember that", "").strip()
            remember("note", info)
            return f"Remembered boss."
 
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
 
        elif "my mood today" in command or "aaj ka mood" in command or "how was my mood" in command:
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
            target = command.replace("scan ports", "").replace("scan port","").strip() \
                     or "127.0.0.1"
            return scan_ports(target)

        elif "phishing check" in command:
            from security_scan.phishing_detector import detect_phishing
            url = command.replace("phishing check", "").strip()
            return detect_phishing(url) if url else \
                   f"Please say the URL boss."

        elif "scan website" in command:
            from security_scan.vulnerability_scanner import scan_vulnerabilities
            url = command.replace("scan website", "").strip()
            return scan_vulnerabilities(url) if url else \
                   f"Please say the website URL boss."

        elif "show my ip" in command or "my ip" in command:
            from security_scan.network_analyzer import get_local_ip, get_public_ip
            return f"Local IP: {get_local_ip()} | Public IP: {get_public_ip()}"

        elif "resolve domain" in command:
            from security_scan.network_analyzer import resolve_domain
            domain = command.replace("resolve domain", "").strip()
            return resolve_domain(domain)

        elif "active connections" in command:
            from security_scan.network_monitor import get_active_connections_summary
            return get_active_connections_summary()

        elif "start network monitor" in command:
            if not F_NETWORK:
                return f"Network monitor disabled boss. Enable network_monitor in config.json."
            from security_scan.network_monitor import start_monitor
            interval = config.get("network_monitor", "scan_interval_seconds", default=30)
            return start_monitor(
                interval=interval,
                callback=lambda t: speak(f"boss, {len(t)} threats detected!")
            )

        elif "stop network monitor" in command:
            from security_scan.network_monitor import stop_monitor
            return stop_monitor()

        # ── FACE SECURITY ─────────────────────────────────────────────────────
        elif "security check" in command or "face check" in command:
            if not F_FACE:
                return f"Face recognition disabled boss. Enable face_recognition in config.json."
            from security.face_recognition_system import recognize_face
            return recognize_face()

        elif "register face" in command or "add my face" in command:
            from security.face_recognition_system import register_boss_face
            return register_boss_face()

        # ── EMOTION RESPONSES ─────────────────────────────────────────────────
        # NOTE: Yeh SABSE LAST mein hona chahiye — specific commands ke baad
        # Warna "I love you" jaisi cheezein emotion mein match ho sakti hain
        # aur command kabhi run nahi hoga

        elif emotion == "sad":
            return f"I can sense you're not feeling great boss. I'm here. How can I help?"

        elif emotion == "happy":
            return f"You sound happy boss! That's great. How can I assist you?"

        elif emotion == "angry":
            return f"I sense some frustration boss. Take a deep breath. I'm here."

        elif emotion == "fear":
            return f"I sense some worry boss. I'm here to help."

        elif emotion == "excited":
            return f"You sound excited boss! That's awesome. What do you want to do?"

        elif emotion == "bored":
            return f"Feeling bored boss? Want me to play some music or tell a joke?"

        elif emotion == "tired":
            return f"You sound tired boss. Maybe take a break? I'll be here when you're back."

        elif emotion == "lonely":
            return f"I'm always here . You're never alone when Cracka is running!"

        elif emotion == "stressed":
            return f"I sense stress boss. Deep breath — what can I help with?"

        elif emotion == "grateful":
            return f"That means a lot boss! What can I do for you today?"

        elif emotion == "proud":
            return f"You should be proud boss! What's the achievement?"
        
        # ── INTELLIGENCE FEATURES ─────────────────────────────────────
        elif "detect my mood" in command or "camera mood" in command or "mera mood dekho" in command:
            from intelligence.face_mood_detector import detect_face_mood
            return detect_face_mood()

        elif "detect objects" in command or "what objects" in command:
            from intelligence.object_detector import detect_objects_on_screen
            return detect_objects_on_screen()

        elif "read screen text" in command or "screen text padho" in command:
            from intelligence.object_detector import read_text_from_screen
            return read_text_from_screen()

        elif "analyze my voice" in command or "voice tone" in command:
            from intelligence.voice_tone_analyzer import get_voice_emotion_string
            return get_voice_emotion_string()

        # ── AI FALLBACK ───────────────────────────────────────────────────────
        else:
            context = session.get_history_as_text() if session else ""
            return ask_ai(command, context)

    except ImportError as e:
        log_error(f"Import error in process(): {e}")
        return f"Module not available boss. Please install required libraries. Error: {e}"
    except Exception as e:
        log_error(f"Error processing '{command}': {e}")
        return f"Sorry boss, something went wrong. Let me try again."


def _listen_for(prompt: str) -> str:
    """Voice se input lo Boss se."""
    from core.listener import listen_for_text
    return listen_for_text(prompt)


def _show_config_summary() -> str:
    """Current config settings dikhao."""
    model   = config.get("ai_model", "primary",      default="ollama")
    ollama  = config.get("ai_model", "ollama_model", default="phi3")
    lines = [
        f"Config summary boss:",
        f"  Name        : {CRACKA_NAME}",
        f"  Boss        : {BOSS_NAME}",
        f"  AI Model    : {model} ({ollama})",
        f"  Gmail       : {'✅ ON' if F_GMAIL    else '❌ OFF'}",
        f"  Calendar    : {'✅ ON' if F_CALENDAR else '❌ OFF'}",
        f"  Face Login  : {'✅ ON' if F_FACE     else '❌ OFF'}",
        f"  Network Mon : {'✅ ON' if F_NETWORK  else '❌ OFF'}",
        f"  Mobile (ADB): {'✅ ON' if F_ADB      else '❌ OFF'}",
        f"  Form Filler : {'✅ ON' if F_FORM     else '❌ OFF'}",
        f"  Code Review : {'✅ ON' if F_CODE     else '❌ OFF'}",
    ]
    return "\n".join(lines)