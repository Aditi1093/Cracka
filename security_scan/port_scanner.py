"""
security_scan/port_scanner.py
Fast threaded port scanner with service identification.
"""

import socket
import threading
from core.logger import log_info

COMMON_SERVICES = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 135: "RPC",
    139: "NetBIOS", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    3306: "MySQL", 3389: "RDP", 5900: "VNC", 6379: "Redis",
    8080: "HTTP-Alt", 8443: "HTTPS-Alt", 27017: "MongoDB",
}


def scan_ports(target: str, start: int = 1, end: int = 1025, timeout: float = 0.3) -> str:
    """
    Scan target host for open ports using threading.
    Returns list of open ports with service names.
    """
    open_ports = []
    lock = threading.Lock()

    # Resolve hostname
    try:
        ip = socket.gethostbyname(target)
    except socket.gaierror:
        return f"Cannot resolve host: {target} Boss."

    def check_port(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((ip, port))
            with lock:
                open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()

    threads = []
    for port in range(start, end + 1):
        t = threading.Thread(target=check_port, args=(port,), daemon=True)
        threads.append(t)
        t.start()

        # Batch to avoid too many threads
        if len(threads) >= 200:
            for t in threads:
                t.join()
            threads = []

    for t in threads:
        t.join()

    open_ports.sort()
    log_info(f"Port scan complete on {target}: {len(open_ports)} open ports")

    if not open_ports:
        return f"No open ports found on {target} Boss."

    lines = [f"Open ports on {target} ({ip}):"]
    for port in open_ports:
        service = COMMON_SERVICES.get(port, "Unknown")
        lines.append(f"  Port {port}: {service}")

    return "\n".join(lines)


def quick_scan(target: str) -> str:
    """Scan only the most common ports quickly."""
    common = [21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3306, 3389, 5900, 8080]
    open_ports = []
    for port in common:
        s = socket.socket()
        s.settimeout(0.5)
        try:
            s.connect((target, port))
            open_ports.append(port)
        except Exception:
            pass
        finally:
            s.close()

    if not open_ports:
        return f"No common ports open on {target} Boss."

    lines = [f"Open common ports on {target}:"]
    for p in open_ports:
        lines.append(f"  {p}: {COMMON_SERVICES.get(p, 'Unknown')}")
    return "\n".join(lines)