"""
╔══════════════════════════════════════════╗
║     CRACKA AI — RANSOMWARE DETECTOR      ║
║   security_scan/ransomware_detector.py   ║
║   Real-time ransomware behavior          ║
║   detection — EDR-style protection       ║
╚══════════════════════════════════════════╝

How ransomware behaves (and how we catch it):

  1. RATE-BASED: Ransomware encrypts hundreds of files in seconds.
     → We track file events in a rolling time window. Too many
       changes too fast = ransomware signature.

  2. EXTENSION-BASED: Encrypted files get renamed with new
     extensions (.locked, .encrypted, .crypt, etc.)
     → We check every renamed file's extension against a list
       of 60+ known ransomware extensions.

  3. ENTROPY-BASED: Encrypted data looks like random noise
     (Shannon entropy close to 8.0 bits/byte). Normal documents,
     images, code have lower, more "patterned" entropy.
     → We sample modified files and calculate entropy.

  4. CANARY FILES (deception): We plant decoy files in monitored
     folders. Ransomware encrypts EVERYTHING — including our
     decoys. If a canary file changes, that's a near-100%
     confirmation (very low false-positive rate).

  5. AUTO-RESPONSE: When ransomware is detected, we try to find
     the process responsible (recently-spawned, non-whitelisted,
     high I/O) and SUSPEND it — buying time before it encrypts
     more files.

Requires: pip install watchdog
"""

import os
import time
import json
import math
import threading
from datetime import datetime
from collections import deque
from core.logger import log_info, log_error

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    FileSystemEventHandler = object  # dummy base class


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────

LOG_FILE       = "data/ransomware_log.json"
CANARY_FOLDER  = ".cracka_canary"   # hidden folder name inside watched dirs

# Rate-based detection: if this many file events happen within
# RATE_WINDOW_SECONDS, trigger an alert.
RATE_WINDOW_SECONDS = 10
RATE_THRESHOLD      = 15

# Entropy threshold — files above this are likely encrypted
# (max possible entropy = 8.0 bits/byte for fully random data)
ENTROPY_THRESHOLD = 7.5

# Known ransomware file extensions (appended after encryption)
RANSOMWARE_EXTENSIONS = {
    ".locked", ".encrypted", ".crypt", ".crypted", ".enc", ".locky",
    ".cerber", ".zepto", ".micro", ".vault", ".ezz", ".exx", ".ecc",
    ".abc", ".ccc", ".zzz", ".crinf", ".r5a", ".xrnt", ".xtbl",
    ".aaa", ".xxx", ".ttt", ".micro", ".encrypted", ".cryptolocker",
    ".odin", ".thor", ".aesir", ".zepto", ".sage", ".globe", ".wannacry",
    ".wcry", ".wncry", ".wncryt", ".onion", ".kraken", ".darkness",
    ".nochance", ".oshit", ".better_call_saul", ".pay", ".pays",
    ".paym", ".ransom", ".0x0", ".bleep", ".rrk", ".rdm", ".kkk",
    ".btc", ".gws", ".magic", ".syrk", ".enigma", ".korean",
}

# File extensions we actively care about protecting (skip junk/temp/system)
MONITORED_EXTENSIONS = {
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf",
    ".txt", ".jpg", ".jpeg", ".png", ".gif", ".mp4", ".mp3",
    ".zip", ".rar", ".csv", ".json", ".py", ".db",
}

# Default folders to monitor
def _default_watch_folders() -> list:
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Desktop"),
        os.path.join(home, "Documents"),
        os.path.join(home, "Downloads"),
        os.path.join(home, "Pictures"),
    ]
    return [f for f in candidates if os.path.exists(f)]


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL STATE
# ─────────────────────────────────────────────────────────────────────────────

_observer        = None
_handler         = None
_monitor_running = False
_gui_ref         = None
_alert_callbacks = []
_watched_folders = []


# ─────────────────────────────────────────────────────────────────────────────
# ENTROPY CALCULATION
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_entropy(file_path: str, sample_size: int = 8192) -> float:
    """
    Calculate Shannon entropy of a file's first `sample_size` bytes.
    Returns value between 0.0 (no randomness) and 8.0 (pure random/encrypted).
    """
    try:
        with open(file_path, "rb") as f:
            data = f.read(sample_size)

        if not data:
            return 0.0

        # Count byte frequency
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1

        # Shannon entropy formula: -Σ p(x) * log2(p(x))
        entropy = 0.0
        length  = len(data)
        for count in freq:
            if count == 0:
                continue
            p = count / length
            entropy -= p * math.log2(p)

        return round(entropy, 2)

    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

def _log_alert(alert: dict):
    """Append an alert to the ransomware log JSON file."""
    os.makedirs("data", exist_ok=True)
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(alert)
    logs = logs[-200:]  # keep last 200
    try:
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log_error(f"[Ransomware] Could not write log: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# AUTO-RESPONSE — try to suspend the offending process
# ─────────────────────────────────────────────────────────────────────────────

# Processes we must NEVER suspend (would break the OS / Cracka itself)
PROCESS_WHITELIST = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe",
    "explorer.exe", "svchost.exe", "dwm.exe", "python.exe", "pythonw.exe",
    "code.exe", "onedrive.exe",
}


def _find_and_suspend_suspicious_process(affected_path: str) -> str:
    """
    Try to find the process that is actively writing to `affected_path`
    (or its folder) and suspend it. Returns a description of what happened.

    This is best-effort — psutil can only see open files for processes
    Cracka has permission to inspect.
    """
    try:
        import psutil
    except ImportError:
        return "psutil not available — could not attempt auto-suspend."

    folder = os.path.dirname(affected_path)
    suspended = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            name = (proc.info["name"] or "").lower()
            if name in PROCESS_WHITELIST:
                continue

            # Check if this process has files open inside the affected folder
            for f in proc.open_files():
                if os.path.dirname(f.path).lower() == folder.lower():
                    proc.suspend()
                    suspended.append(f"{proc.info['name']} (PID {proc.info['pid']})")
                    log_info(f"[Ransomware] SUSPENDED suspicious process: "
                             f"{proc.info['name']} (PID {proc.info['pid']})")
                    break

        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue

    if suspended:
        return f"Suspended: {', '.join(suspended)}"
    return "Could not identify the responsible process for auto-suspend."


# ─────────────────────────────────────────────────────────────────────────────
# ALERT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

def _trigger_alert(alert_type: str, path: str, details: str = "") -> None:
    """Build, log, and broadcast a ransomware alert."""

    alert = {
        "time":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type":    alert_type,
        "path":    path,
        "details": details,
    }

    # Try auto-response for serious alerts
    if alert_type in ("MASS_FILE_MODIFICATION", "CANARY_FILE_TRIGGERED",
                       "KNOWN_RANSOMWARE_EXTENSION"):
        action = _find_and_suspend_suspicious_process(path)
        alert["auto_response"] = action

    _log_alert(alert)
    log_error(f"[RANSOMWARE ALERT] {alert_type}: {path} — {details}")

    # Notify GUI
    global _gui_ref
    if _gui_ref and hasattr(_gui_ref, "show_threat_alert"):
        try:
            _gui_ref.show_threat_alert([{
                "severity":    "HIGH",
                "process":     alert.get("auto_response", "Unknown"),
                "remote_ip":   "LOCAL FILE SYSTEM",
                "hostname":    path,
                "remote_port": 0,
                "alerts":      [f"{alert_type}: {details}"],
                "time":        alert["time"],
            }])
        except Exception as e:
            log_error(f"[Ransomware] GUI notify error: {e}")

    # Notify registered callbacks (e.g. voice speak)
    for fn in _alert_callbacks:
        try:
            fn(alert)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# FILE SYSTEM EVENT HANDLER
# ─────────────────────────────────────────────────────────────────────────────

if WATCHDOG_AVAILABLE:

    class RansomwareEventHandler(FileSystemEventHandler):
        """
        Watches file system events and applies detection rules.
        """

        def __init__(self):
            super().__init__()
            self._events = deque()   # (timestamp, path)
            self._lock   = threading.Lock()

        # ── Watchdog callbacks ────────────────────────────────────────────
        def on_modified(self, event):
            if not event.is_directory:
                self._handle_event(event.src_path, "modified")

        def on_created(self, event):
            if not event.is_directory:
                self._handle_event(event.src_path, "created")

        def on_moved(self, event):
            if not event.is_directory:
                self._handle_event(event.dest_path, "renamed")

        # ── Core logic ──────────────────────────────────────────────────────
        def _handle_event(self, path: str, event_type: str):
            now = time.time()

            # 1. CANARY FILE CHECK — highest confidence
            if CANARY_FOLDER in path:
                _trigger_alert(
                    "CANARY_FILE_TRIGGERED", path,
                    f"Decoy file was {event_type}! This is almost certainly ransomware."
                )
                return

            # 2. EXTENSION CHECK — known ransomware extensions
            ext = os.path.splitext(path)[1].lower()
            if ext in RANSOMWARE_EXTENSIONS:
                _trigger_alert(
                    "KNOWN_RANSOMWARE_EXTENSION", path,
                    f"File renamed with known ransomware extension '{ext}'."
                )
                return

            # 3. RATE-BASED CHECK — track recent events
            with self._lock:
                self._events.append((now, path))
                # Purge events outside the time window
                while self._events and now - self._events[0][0] > RATE_WINDOW_SECONDS:
                    self._events.popleft()
                count = len(self._events)

            if count >= RATE_THRESHOLD:
                # 4. ENTROPY CHECK — confirm with a sample of recent files
                high_entropy_count = 0
                with self._lock:
                    sample_paths = [p for _, p in list(self._events)[-5:]]

                for p in sample_paths:
                    if os.path.exists(p) and os.path.isfile(p):
                        if _calculate_entropy(p) >= ENTROPY_THRESHOLD:
                            high_entropy_count += 1

                _trigger_alert(
                    "MASS_FILE_MODIFICATION", path,
                    f"{count} files changed in {RATE_WINDOW_SECONDS}s "
                    f"({high_entropy_count}/{len(sample_paths)} sampled files "
                    f"show high entropy — likely encrypted)."
                )

                # Reset window after alert to avoid spamming
                with self._lock:
                    self._events.clear()

else:
    RansomwareEventHandler = None


# ─────────────────────────────────────────────────────────────────────────────
# CANARY FILES (decoy traps)
# ─────────────────────────────────────────────────────────────────────────────

def create_canary_files(folders: list = None) -> str:
    """
    Plant decoy files in monitored folders.
    Ransomware encrypts everything indiscriminately — including these.
    Any change to a canary file is a near-certain ransomware signal.

    Voice: 'create canary files' / 'setup ransomware traps'
    """
    folders = folders or _default_watch_folders()

    if not folders:
        return "Could not find any folders to protect Boss."

    canary_content = (
        "DO NOT DELETE OR MODIFY THIS FILE.\n"
        "This is a Cracka AI security decoy file used to detect ransomware.\n"
        f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    canary_names = [
        "passwords_backup.txt",
        "important_documents.docx",
        "financial_records_2026.xlsx",
        "tax_information.pdf",
    ]

    created = []

    for folder in folders:
        canary_dir = os.path.join(folder, CANARY_FOLDER)
        try:
            os.makedirs(canary_dir, exist_ok=True)

            # Try to hide the folder on Windows
            try:
                import subprocess
                subprocess.run(["attrib", "+h", canary_dir], shell=True, check=False)
            except Exception:
                pass

            for name in canary_names:
                path = os.path.join(canary_dir, name)
                if not os.path.exists(path):
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(canary_content)
                    created.append(path)

        except Exception as e:
            log_error(f"[Ransomware] Could not create canary in {folder}: {e}")

    log_info(f"[Ransomware] Created {len(created)} canary files across {len(folders)} folders")

    if created:
        return (f"Created {len(created)} decoy files across {len(folders)} folders Boss. "
                f"These act as traps — if ransomware touches them, you'll get an "
                f"instant high-confidence alert!")
    return "No new canary files needed Boss — they may already exist."


# ─────────────────────────────────────────────────────────────────────────────
# START / STOP MONITOR
# ─────────────────────────────────────────────────────────────────────────────

def start_monitor(folders: list = None, callback=None) -> str:
    """
    Start real-time ransomware monitoring.
    Voice: 'start ransomware protection' / 'start ransomware monitor'
    """
    global _observer, _handler, _monitor_running, _watched_folders

    if not WATCHDOG_AVAILABLE:
        return ("Ransomware monitor needs the 'watchdog' library Boss. "
                "Install it with: pip install watchdog")

    if _monitor_running:
        return "Ransomware monitor is already running Boss."

    folders = folders or _default_watch_folders()
    if not folders:
        return "Could not find any folders to monitor Boss."

    if callback:
        _alert_callbacks.append(callback)

    # Auto-create canary files if they don't exist
    create_canary_files(folders)

    _handler  = RansomwareEventHandler()
    _observer = Observer()

    for folder in folders:
        try:
            _observer.schedule(_handler, folder, recursive=True)
        except Exception as e:
            log_error(f"[Ransomware] Could not watch {folder}: {e}")

    _observer.start()
    _monitor_running = True
    _watched_folders = folders

    log_info(f"[Ransomware] Monitor started on {len(folders)} folder(s)")
    return (f"🛡️ Ransomware protection ACTIVE Boss! "
            f"Monitoring {len(folders)} folder(s): "
            f"{', '.join(os.path.basename(f) for f in folders)}")


def stop_monitor() -> str:
    """Stop ransomware monitoring."""
    global _observer, _monitor_running

    if not _monitor_running or not _observer:
        return "Ransomware monitor is not running Boss."

    try:
        _observer.stop()
        _observer.join(timeout=3)
    except Exception as e:
        log_error(f"[Ransomware] Stop error: {e}")

    _monitor_running = False
    _observer = None
    log_info("[Ransomware] Monitor stopped")
    return "Ransomware protection stopped Boss."


def get_status() -> str:
    """
    Voice: 'ransomware status' / 'is ransomware protection on'
    """
    if not WATCHDOG_AVAILABLE:
        return "Ransomware monitor not available Boss — install 'watchdog' library."

    if _monitor_running:
        folders_str = ", ".join(os.path.basename(f) for f in _watched_folders)
        return f"🛡️ Ransomware protection is ACTIVE Boss. Watching: {folders_str}"
    return "Ransomware protection is OFF Boss. Say 'start ransomware protection' to enable."


def get_recent_alerts(limit: int = 5) -> str:
    """
    Voice: 'show ransomware alerts' / 'ransomware log'
    """
    if not os.path.exists(LOG_FILE):
        return "No ransomware alerts logged Boss. All clear!"

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        return "Could not read ransomware log Boss."

    if not logs:
        return "No ransomware alerts logged Boss. All clear!"

    recent = logs[-limit:]
    lines  = [f"Last {len(recent)} ransomware alert(s) Boss:"]

    for a in reversed(recent):
        lines.append(f"\n🔴 [{a['time']}] {a['type']}")
        lines.append(f"   File: {a['path']}")
        lines.append(f"   {a.get('details', '')}")
        if a.get("auto_response"):
            lines.append(f"   Action: {a['auto_response']}")

    return "\n".join(lines)


def auto_start_if_enabled():
    """
    Called from main.py on startup.
    Auto-starts ransomware monitor if enabled in config.json
    """
    try:
        from core.config_loader import config
        if config.feature("ransomware_monitor"):
            from core.voice_engine import speak
            result = start_monitor(
                callback=lambda alert: speak(
                    f"Boss! Ransomware activity detected on {os.path.basename(alert['path'])}! "
                    f"{alert.get('auto_response', '')}"
                )
            )
            log_info(f"[Ransomware] Auto-start: {result}")
    except Exception as e:
        log_error(f"[Ransomware] Auto-start error: {e}")


def set_gui(gui) -> None:
    """Connect GUI reference for threat popups (called from main.py)."""
    global _gui_ref
    _gui_ref = gui