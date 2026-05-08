"""
security_scan/network_monitor.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cracka AI — Network Threat Monitor

FIXES:
- GUI ke saath properly integrated
- Auto-start config se
- Threat alert GUI popup se connected
- False positives kam kiye (common processes whitelist mein add)
"""

import psutil
import socket
import threading
import json
import os
import time
from datetime import datetime
from core.logger import log_info, log_error

# ── Dangerous ports ───────────────────────────────────────────────────────────
SUSPICIOUS_PORTS = {
    23:    "Telnet (unencrypted)",
    25:    "SMTP (spam/malware)",
    135:   "RPC (remote code risk)",
    139:   "NetBIOS (exploit)",
    445:   "SMB (WannaCry/ransomware)",
    1433:  "MSSQL (database exposed)",
    1434:  "MSSQL UDP",
    3389:  "RDP (brute-force target)",
    4444:  "Metasploit default payload",
    5900:  "VNC (remote desktop)",
    6666:  "IRC (malware C2)",
    6667:  "IRC (malware C2)",
    8080:  "Alt HTTP (proxy/tunnel)",
    9001:  "Tor relay port",
    9030:  "Tor directory",
    31337: "Back Orifice (RAT)",
    12345: "NetBus (trojan)",
    20034: "NetBus 2 (trojan)",
}

# ── Safe processes whitelist (expanded) ───────────────────────────────────────
SAFE_PROCESSES = {
    # Browsers
    "chrome.exe", "msedge.exe", "firefox.exe", "opera.exe", "brave.exe",
    # Dev tools
    "code.exe", "code - insiders.exe", "node.exe", "git.exe",
    "python.exe", "pythonw.exe", "pycharm64.exe",
    # System
    "explorer.exe", "svchost.exe", "lsass.exe", "services.exe",
    "wininit.exe", "taskhostw.exe", "dwm.exe", "conhost.exe",
    "cmd.exe", "powershell.exe", "searchindexer.exe",
    "ntoskrnl.exe", "csrss.exe", "smss.exe", "winlogon.exe",
    "spoolsv.exe", "audiodg.exe", "dashost.exe",
    # Apps
    "discord.exe", "spotify.exe", "steam.exe", "notepad.exe",
    "onedrive.exe", "teams.exe", "slack.exe", "zoom.exe",
    "windowsdefender.exe", "msmpeng.exe", "nissrv.exe",
    # Cracka itself
    "main.py", "cracka",
}

PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "127.", "0.0.0.0", "::1", "fe80")

LOG_FILE       = "data/network_log.json"
_monitor_running  = False
_monitor_thread   = None
_alert_callbacks  = []
_gui_ref          = None   # GUI reference for popup alerts


def _is_private(ip: str) -> bool:
    return ip.startswith(PRIVATE_PREFIXES)


def _get_process(pid: int) -> str:
    try:
        return psutil.Process(pid).name().lower()
    except Exception:
        return "unknown"


def _analyze_connection(conn) -> dict:
    """Analyze one connection. Return alert dict or None if safe."""
    if not conn.raddr:
        return None

    remote_ip   = conn.raddr.ip
    remote_port = conn.raddr.port
    local_port  = conn.laddr.port if conn.laddr else 0
    pid         = conn.pid or 0
    process     = _get_process(pid)
    alerts      = []

    # Skip private IPs completely
    if _is_private(remote_ip):
        return None

    # Skip safe processes
    if process in SAFE_PROCESSES:
        return None

    # Check 1: Known bad remote port
    if remote_port in SUSPICIOUS_PORTS:
        alerts.append(f"Dangerous port {remote_port}: {SUSPICIOUS_PORTS[remote_port]}")

    # Check 2: Known bad local port
    if local_port in SUSPICIOUS_PORTS:
        alerts.append(f"Dangerous local port {local_port}: {SUSPICIOUS_PORTS[local_port]}")

    # Check 3: Unknown process on external IP
    if process not in SAFE_PROCESSES and process != "unknown":
        alerts.append(f"Unknown process '{process}' on external IP {remote_ip}")

    # Check 4: High ephemeral port — only flag if also unknown process
    if remote_port > 49000 and process not in SAFE_PROCESSES:
        alerts.append(f"High port {remote_port} — possible C2 beacon")

    if not alerts:
        return None

    # Resolve hostname
    hostname = remote_ip
    try:
        hostname = socket.gethostbyaddr(remote_ip)[0]
    except Exception:
        pass

    severity = "HIGH" if len(alerts) >= 2 else "MEDIUM"

    return {
        "time":        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "severity":    severity,
        "process":     process,
        "pid":         pid,
        "remote_ip":   remote_ip,
        "hostname":    hostname,
        "remote_port": remote_port,
        "local_port":  local_port,
        "status":      conn.status or "N/A",
        "alerts":      alerts
    }


def scan_connections() -> list:
    """Scan all active connections and return suspicious ones."""
    results = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            found = _analyze_connection(conn)
            if found:
                results.append(found)
    except PermissionError:
        return [{"error": "Run Cracka as Administrator for full scan Boss."}]
    except Exception as e:
        log_error(f"Network scan error: {e}")
        return [{"error": str(e)}]
    return results


def check_network() -> str:
    """Voice command: 'check network' / 'network scan'"""
    results = scan_connections()

    if not results:
        return "Network is clean Boss. No suspicious connections detected."

    if "error" in results[0]:
        return results[0]["error"]

    for r in results:
        _log_alert(r)

    # Show GUI popup if available
    _notify_gui(results)

    high = [r for r in results if r["severity"] == "HIGH"]
    med  = [r for r in results if r["severity"] == "MEDIUM"]

    summary = f"Boss, found {len(results)} suspicious connection(s). "
    if high:
        summary += f"{len(high)} HIGH: "
        summary += "; ".join(
            f"{r['process']} on port {r['remote_port']}" for r in high[:2]
        )
    if med:
        summary += f" {len(med)} medium risk."

    return summary.strip()


def get_active_connections_summary() -> str:
    """Voice command: 'active connections'"""
    try:
        conns  = psutil.net_connections(kind="inet")
        active = [c for c in conns if c.status == "ESTABLISHED" and c.raddr]
        if not active:
            return "No active external connections Boss."

        lines = [f"Active connections ({len(active)}):"]
        for c in active[:8]:
            proc = _get_process(c.pid or 0)
            ip   = c.raddr.ip
            port = c.raddr.port
            if not _is_private(ip):
                lines.append(f"  {proc} → {ip}:{port}")

        return "\n".join(lines) if len(lines) > 1 else "All connections are to private IPs Boss."

    except Exception as e:
        return f"Could not read connections Boss: {e}"


def get_network_report() -> str:
    """Full detailed report for terminal."""
    results = scan_connections()
    if not results:
        return "=== NETWORK CLEAN — No threats ==="
    if "error" in results[0]:
        return results[0]["error"]

    lines = [f"=== CRACKA NETWORK REPORT [{datetime.now().strftime('%H:%M:%S')}] ===\n"]
    for i, r in enumerate(results, 1):
        lines += [
            f"[{r['severity']}] Threat #{i}",
            f"  Process : {r['process']} (PID {r['pid']})",
            f"  Remote  : {r['hostname']}:{r['remote_port']}",
            f"  Local   : port {r['local_port']}",
            f"  Status  : {r['status']}",
            "  Alerts  :",
        ]
        for a in r["alerts"]:
            lines.append(f"    → {a}")
        lines.append("")
    return "\n".join(lines)


def _log_alert(alert: dict):
    """Save alert to JSON log."""
    os.makedirs("data", exist_ok=True)
    logs = []
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE) as f:
                logs = json.load(f)
        except Exception:
            logs = []
    logs.append(alert)
    logs = logs[-500:]
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)


def _notify_gui(threats: list):
    """Show threat alert popup in GUI if available."""
    global _gui_ref
    if _gui_ref and threats:
        try:
            # Thread-safe GUI call
            if hasattr(_gui_ref, 'show_threat_alert'):
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                _gui_ref.show_threat_alert(threats)
        except Exception as e:
            log_error(f"GUI notification error: {e}")


def set_gui(gui) -> None:
    """Connect GUI reference for threat popups."""
    global _gui_ref
    _gui_ref = gui
    log_info("Network monitor connected to GUI")


def register_alert_callback(fn):
    """Register callback for threat alerts."""
    _alert_callbacks.append(fn)


def start_monitor(interval: int = 30, callback=None) -> str:
    """Start background network monitoring."""
    global _monitor_running, _monitor_thread

    if _monitor_running:
        return "Network monitor is already running Boss."

    if callback:
        register_alert_callback(callback)

    _monitor_running = True

    def _loop():
        log_info(f"[NetworkMonitor] Started — scanning every {interval}s")
        while _monitor_running:
            try:
                results = scan_connections()
                if results and "error" not in results[0]:
                    # Only alert if HIGH severity found
                    high = [r for r in results if r["severity"] == "HIGH"]
                    if high:
                        for r in results:
                            _log_alert(r)
                        # Notify GUI
                        _notify_gui(high)
                        # Notify callbacks (voice speak)
                        for fn in _alert_callbacks:
                            try:
                                fn(results)
                            except Exception:
                                pass
            except Exception as e:
                log_error(f"[NetworkMonitor] Loop error: {e}")

            time.sleep(interval)

        log_info("[NetworkMonitor] Stopped")

    _monitor_thread = threading.Thread(target=_loop, daemon=True)
    _monitor_thread.start()
    return f"Network monitoring started Boss. Scanning every {interval} seconds."


def stop_monitor() -> str:
    """Stop background monitoring."""
    global _monitor_running
    _monitor_running = False
    return "Network monitoring stopped Boss."


def monitor_status() -> str:
    return "Running" if _monitor_running else "Stopped"


def auto_start_if_enabled():
    """
    Called from main.py on startup.
    Auto-starts monitor if enabled in config.json
    """
    try:
        from core.config_loader import config
        if config.feature("network_monitor"):
            interval = config.get("network_monitor", "scan_interval_seconds", default=30)
            from core.voice_engine import speak
            start_monitor(
                interval=interval,
                callback=lambda threats: speak(
                    f"Boss, {len(threats)} network threat detected!"
                )
            )
            log_info("Network monitor auto-started from config")
    except Exception as e:
        log_error(f"Network monitor auto-start error: {e}")