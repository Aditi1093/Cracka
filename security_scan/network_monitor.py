"""
security_scan/network_monitor.py
Real-time network threat monitoring for Cracka AI.
Detects suspicious connections, malware ports, unknown processes.
"""

import psutil
import socket
import threading
import json
import os
from datetime import datetime
from core.logger import log_info, log_error

# Known dangerous ports
SUSPICIOUS_PORTS = {
    23: "Telnet (unencrypted)",
    25: "SMTP (spam/malware)",
    135: "RPC (remote code risk)",
    139: "NetBIOS (exploit)",
    445: "SMB (WannaCry/ransomware)",
    1433: "MSSQL (database exposed)",
    1434: "MSSQL UDP",
    3389: "RDP (brute-force target)",
    4444: "Metasploit default payload",
    5900: "VNC (remote desktop)",
    6666: "IRC (malware C2)",
    6667: "IRC (malware C2)",
    8080: "Alt HTTP (proxy/tunnel)",
    9001: "Tor relay port",
    9030: "Tor directory",
    31337: "Back Orifice (RAT)",
    12345: "NetBus (trojan)",
    20034: "NetBus 2 (trojan)",
}

# Safe processes (whitelist)
SAFE_PROCESSES = {
    "chrome.exe", "msedge.exe", "firefox.exe", "code.exe",
    "python.exe", "pythonw.exe", "explorer.exe", "svchost.exe",
    "discord.exe", "spotify.exe", "steam.exe", "notepad.exe",
    "system", "lsass.exe", "services.exe", "wininit.exe",
    "taskhostw.exe", "dwm.exe", "conhost.exe", "cmd.exe",
    "powershell.exe", "searchindexer.exe", "onedrive.exe",
    "windowsdefender.exe", "msMpEng.exe", "teams.exe",
}

# Private IP prefixes (usually safe)
PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "127.", "0.0.0.0", "::1")

LOG_FILE = "data/network_log.json"
_monitor_running = False
_monitor_thread = None
_alert_callbacks = []


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

    remote_ip = conn.raddr.ip
    remote_port = conn.raddr.port
    local_port = conn.laddr.port if conn.laddr else 0
    pid = conn.pid or 0
    process = _get_process(pid)
    alerts = []

    # Check 1: Known bad remote port
    if remote_port in SUSPICIOUS_PORTS:
        alerts.append(f"Dangerous port {remote_port}: {SUSPICIOUS_PORTS[remote_port]}")

    # Check 2: Known bad local port
    if local_port in SUSPICIOUS_PORTS:
        alerts.append(f"Dangerous local port {local_port}: {SUSPICIOUS_PORTS[local_port]}")

    # Check 3: Unknown process → external IP
    if not _is_private(remote_ip) and process not in SAFE_PROCESSES:
        alerts.append(f"Unknown process '{process}' connected to external {remote_ip}")

    # Check 4: Very high ephemeral port on external IP
    if remote_port > 49000 and not _is_private(remote_ip):
        alerts.append(f"High ephemeral port {remote_port} on external IP (possible C2 beacon)")

    # Check 5: Resolve hostname
    hostname = remote_ip
    try:
        hostname = socket.gethostbyaddr(remote_ip)[0]
    except Exception:
        if not _is_private(remote_ip) and alerts:
            alerts.append(f"No hostname resolved for {remote_ip} (raw IP — suspicious)")

    if not alerts:
        return None

    severity = "HIGH" if len(alerts) >= 2 else "MEDIUM"
    return {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "severity": severity,
        "process": process,
        "pid": pid,
        "remote_ip": remote_ip,
        "hostname": hostname,
        "remote_port": remote_port,
        "local_port": local_port,
        "status": conn.status or "N/A",
        "alerts": alerts
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
        return [{"error": "Run Cracka as Administrator for full network scan Boss."}]
    except Exception as e:
        log_error(f"Network scan error: {e}")
        return [{"error": str(e)}]
    return results


def check_network() -> str:
    """Voice command handler — scan and report."""
    results = scan_connections()
    if not results:
        return "Network is clean Boss. No suspicious connections detected."
    if "error" in results[0]:
        return results[0]["error"]

    for r in results:
        _log_alert(r)

    high = [r for r in results if r["severity"] == "HIGH"]
    med = [r for r in results if r["severity"] == "MEDIUM"]

    summary = f"Boss, found {len(results)} suspicious connection(s). "
    if high:
        summary += f"{len(high)} HIGH severity: "
        summary += "; ".join(f"{r['process']} on port {r['remote_port']}" for r in high[:2])
    if med:
        summary += f" {len(med)} medium risk."
    return summary


def get_active_connections_summary() -> str:
    """Return a readable summary of all active connections."""
    try:
        conns = psutil.net_connections(kind="inet")
        active = [c for c in conns if c.status == "ESTABLISHED" and c.raddr]
        if not active:
            return "No active external connections Boss."
        lines = [f"Active connections ({len(active)}):"]
        for c in active[:8]:
            proc = _get_process(c.pid or 0)
            lines.append(f"  {proc} → {c.raddr.ip}:{c.raddr.port}")
        return "\n".join(lines)
    except Exception as e:
        return f"Could not read connections: {e}"


def get_network_report() -> str:
    """Full detailed text report."""
    results = scan_connections()
    if not results:
        return "=== NETWORK CLEAN — No threats detected ==="
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
            f"  Alerts  :",
        ]
        for a in r["alerts"]:
            lines.append(f"    → {a}")
        lines.append("")
    return "\n".join(lines)


def _log_alert(alert: dict):
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


def register_alert_callback(fn):
    _alert_callbacks.append(fn)


def start_monitor(interval: int = 30, callback=None) -> str:
    global _monitor_running, _monitor_thread
    if _monitor_running:
        return "Network monitor is already running Boss."
    if callback:
        register_alert_callback(callback)
    _monitor_running = True

    def _loop():
        log_info("[NetworkMonitor] Started background monitoring")
        while _monitor_running:
            results = scan_connections()
            if results and "error" not in results[0]:
                for r in results:
                    _log_alert(r)
                for fn in _alert_callbacks:
                    try:
                        fn(results)
                    except Exception:
                        pass
            import time
            time.sleep(interval)

    _monitor_thread = threading.Thread(target=_loop, daemon=True)
    _monitor_thread.start()
    return f"Network monitoring started Boss. Scanning every {interval} seconds."


def stop_monitor() -> str:
    global _monitor_running
    _monitor_running = False
    return "Network monitoring stopped Boss."


def monitor_status() -> str:
    return "Running" if _monitor_running else "Stopped"