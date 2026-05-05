"""
security_scan/network_analyzer.py
Network analysis: IP info, DNS, bandwidth monitoring.
"""

import socket
import requests
from core.logger import log_error


def get_local_ip() -> str:
    """Get local machine IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def get_public_ip() -> str:
    """Get public (external) IP address."""
    try:
        r = requests.get("https://api.ipify.org?format=json", timeout=5)
        return r.json()["ip"]
    except Exception as e:
        log_error(f"Public IP error: {e}")
        return "Could not get public IP"


def resolve_domain(domain: str) -> str:
    """Resolve a domain name to IP address."""
    try:
        ip = socket.gethostbyname(domain)
        return f"{domain} → {ip}"
    except socket.gaierror:
        return f"Cannot resolve domain: {domain}"


def get_ip_info(ip: str) -> str:
    """Get geolocation info for an IP address."""
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
        data = r.json()
        country = data.get("country_name", "Unknown")
        city = data.get("city", "Unknown")
        org = data.get("org", "Unknown")
        return f"IP: {ip} | Location: {city}, {country} | ISP: {org}"
    except Exception as e:
        return f"Could not get IP info: {e}"


def get_active_connections() -> list:
    """Get all ESTABLISHED network connections."""
    try:
        import psutil
        conns = []
        for c in psutil.net_connections(kind="inet"):
            if c.status == "ESTABLISHED" and c.raddr:
                try:
                    proc = psutil.Process(c.pid).name() if c.pid else "?"
                except Exception:
                    proc = "?"
                conns.append({
                    "process": proc,
                    "local": f"{c.laddr.ip}:{c.laddr.port}",
                    "remote": f"{c.raddr.ip}:{c.raddr.port}",
                })
        return conns
    except Exception as e:
        log_error(f"Connection list error: {e}")
        return []


def get_network_speed() -> str:
    """Get network interface stats (bytes sent/received)."""
    try:
        import psutil
        stats = psutil.net_io_counters()
        sent_mb = stats.bytes_sent / (1024 * 1024)
        recv_mb = stats.bytes_recv / (1024 * 1024)
        return f"Sent: {sent_mb:.1f} MB | Received: {recv_mb:.1f} MB (since last boot)"
    except Exception as e:
        return f"Network stats error: {e}"