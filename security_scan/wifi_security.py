"""
╔══════════════════════════════════════════╗
║     CRACKA AI — WI-FI SECURITY CHECKER   ║
║   security_scan/wifi_security.py         ║
║   Checks saved Wi-Fi networks for weak    ║
║   encryption and exposes saved passwords  ║
║   (with Boss's permission)                ║
╚══════════════════════════════════════════╝

Windows only — uses 'netsh wlan' commands.
On Linux/Mac, returns a friendly "not supported" message
(same pattern as cve_scanner.py's installed-software check).
"""

import subprocess
import platform
import re
from core.logger import log_info, log_error

# Encryption types ranked worst → best
WEAK_ENCRYPTION = {"none", "open", "wep", "wpa", "wpa-personal"}
OKAY_ENCRYPTION = {"wpa2", "wpa2-personal"}
STRONG_ENCRYPTION = {"wpa3", "wpa3-personal", "wpa2-enterprise", "wpa3-enterprise"}


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _run_netsh(args: list) -> str:
    """Run a netsh wlan command and return stdout, or '' on failure."""
    try:
        result = subprocess.run(
            ["netsh", "wlan"] + args,
            capture_output=True, text=True, timeout=10
        )
        return result.stdout
    except FileNotFoundError:
        return ""
    except Exception as e:
        log_error(f"[WiFiSecurity] netsh error: {e}")
        return ""


def get_saved_networks() -> list:
    """
    Returns list of saved Wi-Fi profile names.
    Windows only.
    """
    if not _is_windows():
        return []

    output = _run_netsh(["show", "profiles"])
    if not output:
        return []

    profiles = []
    for line in output.splitlines():
        match = re.search(r"All User Profile\s*:\s*(.+)", line)
        if match:
            profiles.append(match.group(1).strip())

    return profiles


def get_network_security_info(profile_name: str) -> dict:
    """
    Get encryption/auth type and password (if available) for one
    saved Wi-Fi profile.
    Returns dict: {"name", "auth", "cipher", "password"}
    """
    output = _run_netsh(["show", "profile", f"name={profile_name}", "key=clear"])
    if not output:
        return {}

    info = {"name": profile_name, "auth": "Unknown", "cipher": "Unknown", "password": None}

    for line in output.splitlines():
        line = line.strip()

        auth_match = re.match(r"Authentication\s*:\s*(.+)", line)
        if auth_match:
            info["auth"] = auth_match.group(1).strip()

        cipher_match = re.match(r"Cipher\s*:\s*(.+)", line)
        if cipher_match:
            info["cipher"] = cipher_match.group(1).strip()

        pw_match = re.match(r"Key Content\s*:\s*(.+)", line)
        if pw_match:
            info["password"] = pw_match.group(1).strip()

    return info


# ─────────────────────────────────────────────────────────────────────────────
# VOICE COMMANDS
# ─────────────────────────────────────────────────────────────────────────────

def check_wifi_security() -> str:
    """
    Voice: 'check wifi security' / 'wifi security check' / 'scan wifi'

    Scans all saved Wi-Fi networks and flags any using weak/no
    encryption (Open, WEP, WPA-only). Does NOT show passwords here —
    use 'show wifi password <network>' for that, since exposing
    passwords for all networks at once is a privacy/safety risk.
    """
    if not _is_windows():
        return ("Wi-Fi security check works on Windows only Boss "
                "(uses 'netsh wlan' commands). This feature isn't "
                "available on Linux/Mac.")

    profiles = get_saved_networks()
    if not profiles:
        return "No saved Wi-Fi networks found Boss, or Wi-Fi adapter not available."

    weak = []
    okay = []
    strong = []
    unknown = []

    for name in profiles:
        info = get_network_security_info(name)
        if not info:
            unknown.append(name)
            continue

        auth = info["auth"].lower().replace(" ", "-")

        if any(w in auth for w in WEAK_ENCRYPTION):
            weak.append((name, info["auth"]))
        elif any(o in auth for o in OKAY_ENCRYPTION):
            okay.append((name, info["auth"]))
        elif any(s in auth for s in STRONG_ENCRYPTION):
            strong.append((name, info["auth"]))
        else:
            unknown.append(name)

    log_info(f"[WiFiSecurity] Scanned {len(profiles)} networks: "
             f"{len(weak)} weak, {len(okay)} okay, {len(strong)} strong")

    lines = [f"Wi-Fi security scan complete Boss — {len(profiles)} saved network(s):"]

    if weak:
        lines.append(f"\n🔴 WEAK ENCRYPTION ({len(weak)}) — vulnerable to attacks:")
        for name, auth in weak:
            lines.append(f"  • {name} — {auth}")
        lines.append("  Consider removing these or upgrading the router's security.")

    if okay:
        lines.append(f"\n🟡 OK ({len(okay)}) — WPA2, decent but WPA3 is better:")
        for name, auth in okay:
            lines.append(f"  • {name} — {auth}")

    if strong:
        lines.append(f"\n🟢 STRONG ({len(strong)}):")
        for name, auth in strong:
            lines.append(f"  • {name} — {auth}")

    if unknown:
        lines.append(f"\n⚪ Could not determine encryption for: {', '.join(unknown)}")

    if not weak:
        lines.append("\nNo critically weak networks found Boss!")

    return "\n".join(lines)


def show_wifi_password(profile_name: str) -> str:
    """
    Voice: 'show wifi password <network name>' / 'wifi password for <network>'

    Shows the saved password for ONE specific Wi-Fi network.
    Requires the network name to be spoken explicitly — Cracka will
    not dump all passwords at once for safety.
    """
    if not _is_windows():
        return "Wi-Fi password lookup works on Windows only Boss."

    if not profile_name or not profile_name.strip():
        return "Please tell me which Wi-Fi network Boss, e.g. 'wifi password for HomeNetwork'."

    profile_name = profile_name.strip()

    profiles = get_saved_networks()
    # Case-insensitive match against saved profiles
    match = next((p for p in profiles if p.lower() == profile_name.lower()), None)

    if not match:
        # Try partial match
        match = next((p for p in profiles if profile_name.lower() in p.lower()), None)

    if not match:
        available = ", ".join(profiles) if profiles else "none"
        return f"No saved network matching '{profile_name}' Boss. Saved networks: {available}"

    info = get_network_security_info(match)

    if not info.get("password"):
        return (f"'{match}' is saved but I can't retrieve its password Boss "
                f"— it may be an open network or require admin rights "
                f"(try running Cracka as Administrator).")

    log_info(f"[WiFiSecurity] Password retrieved for '{match}'")

    return (f"Network: {match}\n"
            f"Security: {info['auth']}\n"
            f"Password: {info['password']}")


def list_saved_wifi_networks() -> str:
    """
    Voice: 'list wifi networks' / 'saved wifi networks'
    """
    if not _is_windows():
        return "This feature works on Windows only Boss."

    profiles = get_saved_networks()
    if not profiles:
        return "No saved Wi-Fi networks found Boss."

    lines = [f"Saved Wi-Fi networks Boss ({len(profiles)}):"]
    for p in profiles:
        lines.append(f"  • {p}")

    return "\n".join(lines)