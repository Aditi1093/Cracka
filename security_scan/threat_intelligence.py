"""
╔══════════════════════════════════════════╗
║     CRACKA AI — THREAT INTELLIGENCE      ║
║   security_scan/threat_intelligence.py   ║
║   VirusTotal + HaveIBeenPwned checks     ║
╚══════════════════════════════════════════╝

Features:
  - check_url_virustotal(url)      → URL malware/phishing check
  - check_ip_virustotal(ip)        → IP reputation check
  - check_password_pwned(password) → Password leak check (FREE, no key!)
  - check_email_pwned(email)       → Email breach check (needs HIBP API key)

Setup:
  VirusTotal:
    1. Sign up free: https://www.virustotal.com/gui/join-us
    2. Get API key from your profile
    3. Add to data/credentials.json:
       {"virustotal_api_key": "your_key_here"}

  HaveIBeenPwned (password check):
    - NO API KEY NEEDED — uses free k-anonymity API

  HaveIBeenPwned (email breach check):
    - Needs paid API key (https://haveibeenpwned.com/API/Key)
    - Add to data/credentials.json:
       {"hibp_api_key": "your_key_here"}
"""

import os
import json
import time
import hashlib
import base64
import requests
from core.logger import log_info, log_error

CREDENTIALS_FILE = "data/credentials.json"

VT_BASE_URL   = "https://www.virustotal.com/api/v3"
HIBP_PWNED_PW = "https://api.pwnedpasswords.com/range/"
HIBP_BREACH   = "https://haveibeenpwned.com/api/v3/breachedaccount/"


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get_key(name: str) -> str:
    """
    Read an API key from environment variable OR data/credentials.json.
    name examples: 'virustotal_api_key', 'hibp_api_key'
    """
    env_name = name.upper()
    key = os.environ.get(env_name, "").strip()
    if key:
        return key

    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                creds = json.load(f)
            return creds.get(name, "").strip()
    except Exception as e:
        log_error(f"[ThreatIntel] Could not read {CREDENTIALS_FILE}: {e}")

    return ""


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — URL CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_url_virustotal(url: str) -> str:
    """
    Check a URL against VirusTotal's 70+ antivirus engines.
    Voice: 'virustotal check <url>'
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Get a free key at virustotal.com and add it to "
                "data/credentials.json as 'virustotal_api_key'.")

    if not url.startswith("http"):
        url = "https://" + url

    headers = {"x-apikey": api_key}

    try:
        # Step 1: Submit URL for analysis (VT needs URL ID = base64 of URL)
        url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")

        # Step 2: Try to get existing report first (faster, no quota use)
        r = requests.get(f"{VT_BASE_URL}/urls/{url_id}", headers=headers, timeout=10)

        if r.status_code == 404:
            # Not analyzed yet — submit it
            submit = requests.post(
                f"{VT_BASE_URL}/urls",
                headers=headers,
                data={"url": url},
                timeout=10
            )
            if submit.status_code != 200:
                return f"Could not submit URL to VirusTotal Boss. Status: {submit.status_code}"

            log_info(f"[VirusTotal] Submitted new URL for analysis: {url}")
            return (f"URL submitted to VirusTotal Boss. "
                    f"Analysis takes ~30 seconds — try the check again shortly.")

        if r.status_code == 401:
            return "VirusTotal API key is invalid Boss. Please check data/credentials.json."

        if r.status_code != 200:
            return f"VirusTotal error Boss. Status: {r.status_code}"

        data  = r.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]

        malicious  = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless   = stats.get("harmless", 0)
        undetected = stats.get("undetected", 0)
        total      = malicious + suspicious + harmless + undetected

        log_info(f"[VirusTotal] {url} → {malicious} malicious / {total} engines")

        if malicious > 0:
            return (f"🔴 DANGER Boss! {malicious} out of {total} security engines "
                    f"flagged this URL as MALICIOUS: {url}")
        elif suspicious > 0:
            return (f"🟡 CAUTION Boss. {suspicious} engines flagged this URL "
                    f"as suspicious: {url}")
        else:
            return (f"🟢 SAFE Boss. {harmless} engines checked '{url}' "
                    f"and found no threats.")

    except requests.exceptions.Timeout:
        return "VirusTotal request timed out Boss."
    except Exception as e:
        log_error(f"[VirusTotal] URL check error: {e}")
        return f"Could not check URL with VirusTotal Boss: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — IP CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_ip_virustotal(ip: str) -> str:
    """
    Check an IP address reputation on VirusTotal.
    Voice: 'virustotal check ip <ip address>'
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Get a free key at virustotal.com and add it to "
                "data/credentials.json as 'virustotal_api_key'.")

    headers = {"x-apikey": api_key}

    try:
        r = requests.get(f"{VT_BASE_URL}/ip_addresses/{ip}", headers=headers, timeout=10)

        if r.status_code == 401:
            return "VirusTotal API key is invalid Boss. Please check data/credentials.json."

        if r.status_code == 404:
            return f"No data found for IP {ip} Boss."

        if r.status_code != 200:
            return f"VirusTotal error Boss. Status: {r.status_code}"

        data  = r.json()
        attrs = data["data"]["attributes"]
        stats = attrs.get("last_analysis_stats", {})

        malicious = stats.get("malicious", 0)
        country   = attrs.get("country", "Unknown")
        owner     = attrs.get("as_owner", "Unknown")

        log_info(f"[VirusTotal] IP {ip} → {malicious} malicious flags")

        if malicious > 0:
            return (f"🔴 DANGER Boss! IP {ip} ({owner}, {country}) was flagged "
                    f"MALICIOUS by {malicious} security engines.")
        else:
            return (f"🟢 SAFE Boss. IP {ip} belongs to {owner} ({country}). "
                    f"No threats detected.")

    except requests.exceptions.Timeout:
        return "VirusTotal request timed out Boss."
    except Exception as e:
        log_error(f"[VirusTotal] IP check error: {e}")
        return f"Could not check IP with VirusTotal Boss: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — FILE HASH CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_file_virustotal(file_path: str) -> str:
    """
    Check a local file against VirusTotal using its SHA256 hash.
    Voice: 'virustotal check file <path>'
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Add 'virustotal_api_key' to data/credentials.json.")

    if not os.path.exists(file_path):
        return f"File not found Boss: {file_path}"

    try:
        # Calculate SHA256 hash
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        headers = {"x-apikey": api_key}
        r = requests.get(f"{VT_BASE_URL}/files/{file_hash}", headers=headers, timeout=10)

        if r.status_code == 404:
            return (f"File not in VirusTotal database Boss "
                    f"(hash: {file_hash[:16]}...). It may be new/unique.")

        if r.status_code == 401:
            return "VirusTotal API key is invalid Boss."

        if r.status_code != 200:
            return f"VirusTotal error Boss. Status: {r.status_code}"

        data  = r.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]
        malicious = stats.get("malicious", 0)
        total     = sum(stats.values())

        log_info(f"[VirusTotal] File {file_path} → {malicious}/{total} malicious")

        if malicious > 0:
            return (f"🔴 DANGER Boss! {malicious} out of {total} engines "
                    f"flagged '{os.path.basename(file_path)}' as MALICIOUS!")
        else:
            return f"🟢 SAFE Boss. '{os.path.basename(file_path)}' looks clean."

    except Exception as e:
        log_error(f"[VirusTotal] File check error: {e}")
        return f"Could not check file with VirusTotal Boss: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# HAVEIBEENPWNED — PASSWORD CHECK (FREE — no API key needed!)
# ─────────────────────────────────────────────────────────────────────────────

def check_password_pwned(password: str) -> str:
    """
    Check if a password has appeared in known data breaches.
    Uses k-anonymity — only sends first 5 chars of hash, password
    itself NEVER leaves your computer. 100% free, no API key.

    Voice: 'check password' (then Cracka will ask for the password)
    """
    if not password:
        return "Please provide a password to check Boss."

    try:
        # SHA1 hash of password (uppercase)
        sha1 = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        # Send only first 5 chars — k-anonymity model
        r = requests.get(f"{HIBP_PWNED_PW}{prefix}", timeout=8)

        if r.status_code != 200:
            return f"Could not check password Boss. Status: {r.status_code}"

        # Response is a list of "SUFFIX:COUNT" lines
        for line in r.text.splitlines():
            line_suffix, count = line.split(":")
            if line_suffix == suffix:
                count = int(count)
                log_info(f"[HIBP] Password found in {count} breaches")
                return (f"🔴 WARNING Boss! This password has been seen "
                        f"{count:,} times in data breaches! "
                        f"Please change it immediately and never reuse it.")

        log_info("[HIBP] Password not found in breaches")
        return "🟢 Good news Boss! This password was not found in any known breach."

    except requests.exceptions.Timeout:
        return "Password check timed out Boss."
    except Exception as e:
        log_error(f"[HIBP] Password check error: {e}")
        return f"Could not check password Boss: {e}"


def check_password_voice() -> str:
    """
    Voice-guided password breach check.
    Asks Boss to type the password (NOT speak it, for privacy).
    """
    from core.voice_engine import speak
    speak("For privacy, please type your password in the terminal and press Enter Boss.")

    try:
        import getpass
        password = getpass.getpass("Type password (hidden): ")
    except Exception:
        password = input("Type password: ")

    return check_password_pwned(password)


# ─────────────────────────────────────────────────────────────────────────────
# HAVEIBEENPWNED — EMAIL BREACH CHECK (needs paid API key)
# ─────────────────────────────────────────────────────────────────────────────

def check_email_pwned(email: str) -> str:
    """
    Check if an email address appeared in known data breaches.
    NOTE: HaveIBeenPwned now requires a PAID API key for this endpoint
    (https://haveibeenpwned.com/API/Key — ~$3.50/month).

    Voice: 'check email breach <email>'
    """
    api_key = _get_key("hibp_api_key")
    if not api_key:
        return ("Email breach check needs a HaveIBeenPwned API key Boss "
                "(paid, ~$3.50/month). Get it at haveibeenpwned.com/API/Key "
                "and add 'hibp_api_key' to data/credentials.json. "
                "For free password checks, say 'check password' instead.")

    headers = {
        "hibp-api-key": api_key,
        "user-agent":   "Cracka-AI-Security-Scanner"
    }

    try:
        r = requests.get(
            f"{HIBP_BREACH}{email}?truncateResponse=false",
            headers=headers,
            timeout=10
        )

        if r.status_code == 404:
            return f"🟢 Good news Boss! No breaches found for {email}."

        if r.status_code == 401:
            return "HaveIBeenPwned API key is invalid Boss."

        if r.status_code == 429:
            return "Too many requests Boss. Please wait a moment and try again."

        if r.status_code != 200:
            return f"HaveIBeenPwned error Boss. Status: {r.status_code}"

        breaches = r.json()
        names = [b.get("Name", "Unknown") for b in breaches]

        log_info(f"[HIBP] {email} found in {len(names)} breaches")

        return (f"🔴 WARNING Boss! {email} was found in {len(names)} "
                f"data breach(es): {', '.join(names[:5])}"
                f"{'...' if len(names) > 5 else ''}. "
                f"Please change passwords for these accounts immediately!")

    except requests.exceptions.Timeout:
        return "Email breach check timed out Boss."
    except Exception as e:
        log_error(f"[HIBP] Email check error: {e}")
        return f"Could not check email Boss: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# COMBINED QUICK SCAN
# ─────────────────────────────────────────────────────────────────────────────

def quick_threat_check(target: str) -> str:
    """
    Smart router — detects if target is a URL, IP, or email
    and runs the appropriate check.
    Voice: 'threat check <url/ip/email>'
    """
    target = target.strip()

    # Email check
    if "@" in target and "." in target.split("@")[-1]:
        return check_email_pwned(target)

    # IP address check (simple pattern: 4 numbers separated by dots)
    parts = target.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return check_ip_virustotal(target)

    # Otherwise treat as URL
    return check_url_virustotal(target)