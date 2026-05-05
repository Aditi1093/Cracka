"""
automation/app_control.py
Open and close applications on Windows.
"""

import os
import webbrowser
import subprocess
from core.logger import log_info, log_error

# Map of app names to their open commands
OPEN_COMMANDS = {
    # Browsers
    "chrome":       "start chrome",
    "edge":         "start msedge",
    "firefox":      "start firefox",
    "opera":        "start opera",
    "brave":        r'start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"',

    # Coding
    "vscode":       "code",
    "code":         "code",
    "visual studio": "devenv",
    "pycharm":      "pycharm64",
    "notepad++":    "notepad++",
    "sublime":      "subl",
    "android studio": "studio64",

    # Office
    "word":         "start winword",
    "excel":        "start excel",
    "powerpoint":   "start powerpnt",
    "outlook":      "start outlook",
    "teams":        "start msteams",
    "onenote":      "start onenote",

    # System
    "notepad":      "start notepad",
    "calculator":   "start calc",
    "paint":        "start mspaint",
    "cmd":          "start cmd",
    "powershell":   "start powershell",
    "task manager": "start taskmgr",
    "settings":     "start ms-settings:",
    "explorer":     "explorer",
    "files":        "explorer",
    "control panel": "control",
    "registry":     "regedit",
    "disk manager": "diskmgmt.msc",

    # Communication
    "discord":      r'start "" "%LOCALAPPDATA%\Discord\Update.exe" --processStart Discord.exe',
    "telegram":     r'start "" "%APPDATA%\Telegram Desktop\Telegram.exe"',
    "slack":        "start slack",
    "zoom":         "start zoom",
    "skype":        "start skype",

    # Media
    "vlc":          "start vlc",
    "spotify":      "start spotify",
    "itunes":       "start itunes",

    # Utilities
    "obs":          "start obs64",
    "steam":        r'start "" "C:\Program Files (x86)\Steam\Steam.exe"',
    "7zip":         "start 7zFM",
    "winrar":       "start winrar",
}

# Map of app names to their process names for kill
CLOSE_COMMANDS = {
    "chrome":       "chrome.exe",
    "edge":         "msedge.exe",
    "firefox":      "firefox.exe",
    "code":         "Code.exe",
    "vscode":       "Code.exe",
    "notepad":      "notepad.exe",
    "paint":        "mspaint.exe",
    "cmd":          "cmd.exe",
    "powershell":   "powershell.exe",
    "discord":      "Discord.exe",
    "telegram":     "Telegram.exe",
    "slack":        "slack.exe",
    "zoom":         "Zoom.exe",
    "vlc":          "vlc.exe",
    "spotify":      "Spotify.exe",
    "obs":          "obs64.exe",
    "word":         "WINWORD.EXE",
    "excel":        "EXCEL.EXE",
    "powerpoint":   "POWERPNT.EXE",
    "whatsapp":     "WhatsApp.exe",
}

# Website shortcuts
WEBSITES = {
    "youtube":      "https://youtube.com",
    "google":       "https://google.com",
    "chatgpt":      "https://chat.openai.com",
    "github":       "https://github.com",
    "gmail":        "https://mail.google.com",
    "google drive": "https://drive.google.com",
    "netflix":      "https://netflix.com",
    "amazon":       "https://amazon.com",
    "instagram":    "https://instagram.com",
    "twitter":      "https://twitter.com",
    "linkedin":     "https://linkedin.com",
    "stackoverflow":"https://stackoverflow.com",
    "reddit":       "https://reddit.com",
    "wikipedia":    "https://wikipedia.org",
    "whatsapp web": "https://web.whatsapp.com",
}


def open_app(command: str) -> str:
    """Open an application or website from voice command."""
    command = command.lower()

    # Check websites first
    for name, url in WEBSITES.items():
        if name in command:
            webbrowser.open(url)
            log_info(f"Opened website: {name}")
            return f"Opened {name} Boss."

    # WhatsApp desktop
    if "whatsapp" in command:
        os.system("start shell:AppsFolder\\5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App")
        return "Opened WhatsApp Boss."

    # Check installed apps
    for name, cmd in OPEN_COMMANDS.items():
        if name in command:
            try:
                os.system(cmd)
                log_info(f"Opened app: {name}")
                return f"Opened {name} Boss."
            except Exception as e:
                log_error(f"Failed to open {name}: {e}")
                return f"Could not open {name} Boss."

    return "Application not recognized Boss."


def close_app(command: str) -> str:
    """Close an application from voice command."""
    command = command.lower()
    for name, proc in CLOSE_COMMANDS.items():
        if name in command:
            result = os.system(f"taskkill /f /im {proc}")
            if result == 0:
                log_info(f"Closed: {name}")
                return f"Closed {name} Boss."
            else:
                return f"{name} was not running Boss."
    return "Application not recognized Boss."


def list_running_apps() -> str:
    """List currently running applications."""
    try:
        import psutil
        apps = set()
        for proc in psutil.process_iter(['name']):
            name = proc.info['name']
            if name and not name.lower().startswith('svc') and '.exe' in name.lower():
                apps.add(name.replace('.exe', '').replace('.EXE', ''))
        top = sorted(list(apps))[:15]
        return "Running apps: " + ", ".join(top)
    except Exception as e:
        return f"Could not list apps: {e}"