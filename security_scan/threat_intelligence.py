"""
╔══════════════════════════════════════════╗
║     CRACKA AI — THREAT INTELLIGENCE      ║
║   security_scan/threat_intelligence.py   ║
║   VirusTotal + HaveIBeenPwned checks     ║
╚══════════════════════════════════════════╝

Features:
  - check_url_virustotal(url)      → URL malware/phishing check (with auto re-poll)
  - check_ip_virustotal(ip)        → IP reputation + geolocation
  - check_domain_virustotal(domain)→ Domain reputation + categories (NEW)
  - check_file_virustotal(path)    → File hash check
  - check_password_pwned(password) → Password leak check (FREE, no key!) + local pre-check
  - check_password_voice()         → Voice-guided password check
  - check_email_pwned(email)       → Email breach check (needs HIBP API key)
  - quick_threat_check(target)     → Auto-detect URL/IP/domain/email and route

Setup:
  VirusTotal:
    1. Sign up free: https://www.virustotal.com/gui/join-us
    2. Get API key from your profile
    3. Add to data/credentials.json:
       {"virustotal_api_key": "your_key_here"}
    Free tier limit: 4 requests/minute, 500/day

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
IPAPI_URL     = "https://ipapi.co/"

# ─────────────────────────────────────────────────────────────────────────────
# COMMON PASSWORDS — instant local pre-check, no API call needed
# Checking these locally first means Cracka can warn instantly without
# hitting HIBP, and still works for the most obvious cases even offline.
# ─────────────────────────────────────────────────────────────────────────────
COMMON_PASSWORDS = {
    "123456", "123456789", "qwerty", "password", "12345", "12345678",
    "111111", "1234567", "123123", "qwerty123", "1q2w3e4r", "1234567890",
    "abc123", "654321", "123321", "qwertyuiop", "iloveyou",
    "000000", "admin", "letmein", "monkey", "dragon", "football",
    "password1", "welcome", "login", "princess", "qwerty1", "solo",
    "passw0rd", "starwars", "freedom", "whatever", "trustno1", "killer",
}


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
# SHARED VT REQUEST HELPER — handles timeout / 401 / 429 consistently
# ─────────────────────────────────────────────────────────────────────────────

def _vt_get(endpoint: str, headers: dict, timeout: int = 10):
    """
    Wrapper around requests.get for VT endpoints.
    Returns (response, error_message). If error_message is not None,
    the caller should return it directly to the user; response is None
    in that case.
    """
    try:
        r = requests.get(f"{VT_BASE_URL}{endpoint}", headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        return None, "VirusTotal request timed out Boss."
    except Exception as e:
        return None, f"Could not reach VirusTotal Boss: {e}"

    if r.status_code == 401:
        return None, "VirusTotal API key is invalid Boss. Please check data/credentials.json."

    if r.status_code == 429:
        return None, ("VirusTotal rate limit hit Boss (free tier = 4 requests/minute, "
                       "500/day). Please wait a bit and try again.")

    return r, None


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — URL CHECK (with auto wait-and-poll for new submissions)
# ─────────────────────────────────────────────────────────────────────────────

def check_url_virustotal(url: str, _poll_attempts: int = 0) -> str:
    """
    Check a URL against VirusTotal's 70+ antivirus engines.
    Voice: 'virustotal check <url>'

    UPGRADE: if the URL hasn't been analyzed before, Cracka now submits
    it AND automatically polls for the result a couple of times
    (with short waits) instead of just telling Boss to "try again later".
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Get a free key at virustotal.com and add it to "
                "data/credentials.json as 'virustotal_api_key'.")

    if not url.startswith("http"):
        url = "https://" + url

    headers = {"x-apikey": api_key}
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")

    r, err = _vt_get(f"/urls/{url_id}", headers)
    if err:
        return err

    if r.status_code == 404:
        # Not analyzed yet — submit it
        try:
            submit = requests.post(
                f"{VT_BASE_URL}/urls",
                headers=headers,
                data={"url": url},
                timeout=10
            )
        except requests.exceptions.Timeout:
            return "VirusTotal submission timed out Boss."
        except Exception as e:
            return f"Could not submit URL to VirusTotal Boss: {e}"

        if submit.status_code == 429:
            return "VirusTotal rate limit hit Boss. Please wait a bit and try again."

        if submit.status_code not in (200, 201):
            return f"Could not submit URL to VirusTotal Boss. Status: {submit.status_code}"

        log_info(f"[VirusTotal] Submitted new URL for analysis: {url}")

        # UPGRADE: auto wait-and-poll instead of just telling Boss to retry.
        # VT analysis is usually ready within 10-20 seconds for URLs.
        if _poll_attempts < 2:
            wait_time = 8 if _poll_attempts == 0 else 12
            log_info(f"[VirusTotal] Waiting {wait_time}s before polling for results...")
            time.sleep(wait_time)
            return check_url_virustotal(url, _poll_attempts=_poll_attempts + 1)

        return (f"URL submitted to VirusTotal Boss and analysis is still in progress. "
                f"Say 'virustotal check {url}' again in about 30 seconds for the result.")

    if r.status_code != 200:
        return f"VirusTotal error Boss. Status: {r.status_code}"

    data  = r.json()
    attrs = data["data"]["attributes"]
    stats = attrs.get("last_analysis_stats", {})

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


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — IP CHECK (merged with geolocation from ipapi.co)
# ─────────────────────────────────────────────────────────────────────────────

def check_ip_virustotal(ip: str) -> str:
    """
    Check an IP address reputation on VirusTotal, merged with
    geolocation info (city/region/country/ISP) from ipapi.co.
    Voice: 'virustotal check ip <ip address>'
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Get a free key at virustotal.com and add it to "
                "data/credentials.json as 'virustotal_api_key'.")

    headers = {"x-apikey": api_key}

    r, err = _vt_get(f"/ip_addresses/{ip}", headers)
    if err:
        return err

    if r.status_code == 404:
        return f"No data found for IP {ip} Boss."

    if r.status_code != 200:
        return f"VirusTotal error Boss. Status: {r.status_code}"

    data  = r.json()
    attrs = data["data"]["attributes"]
    stats = attrs.get("last_analysis_stats", {})

    malicious  = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    country    = attrs.get("country", "Unknown")
    owner      = attrs.get("as_owner", "Unknown")

    log_info(f"[VirusTotal] IP {ip} → {malicious} malicious flags")

    # UPGRADE: merge in geolocation (city/region) from ipapi.co for richer context
    geo_line = ""
    try:
        geo = requests.get(f"{IPAPI_URL}{ip}/json/", timeout=5).json()
        city   = geo.get("city", "")
        region = geo.get("region", "")
        if city or region:
            geo_line = f" Location: {', '.join(p for p in [city, region] if p)}."
    except Exception as e:
        log_error(f"[ThreatIntel] Geolocation lookup failed: {e}")

    if malicious > 0:
        return (f"🔴 DANGER Boss! IP {ip} ({owner}, {country}) was flagged "
                f"MALICIOUS by {malicious} security engines.{geo_line}")
    elif suspicious > 0:
        return (f"🟡 CAUTION Boss. IP {ip} ({owner}, {country}) was flagged "
                f"suspicious by {suspicious} engines.{geo_line}")
    else:
        return (f"🟢 SAFE Boss. IP {ip} belongs to {owner} ({country}).{geo_line} "
                f"No threats detected.")


# ─────────────────────────────────────────────────────────────────────────────
# VIRUSTOTAL — DOMAIN REPUTATION CHECK (NEW)
# ─────────────────────────────────────────────────────────────────────────────

def check_domain_virustotal(domain: str) -> str:
    """
    NEW: Check a domain's reputation on VirusTotal — separate from URL
    check. Domains carry their own reputation score and category tags
    (e.g. "phishing", "malware", "gambling") independent of any
    specific URL path, useful for "is this site generally trustworthy"
    questions.

    Voice: 'check domain <domain>' / 'domain reputation <domain>'
    """
    api_key = _get_key("virustotal_api_key")
    if not api_key:
        return ("VirusTotal API key not set Boss. "
                "Get a free key at virustotal.com and add it to "
                "data/credentials.json as 'virustotal_api_key'.")

    domain = domain.strip().lower()
    # Strip scheme/path if Boss said a full URL by mistake
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    if not domain:
        return "Please say a domain name Boss, like 'check domain example.com'."

    headers = {"x-apikey": api_key}

    r, err = _vt_get(f"/domains/{domain}", headers)
    if err:
        return err

    if r.status_code == 404:
        return f"No VirusTotal data found for domain '{domain}' Boss."

    if r.status_code != 200:
        return f"VirusTotal error Boss. Status: {r.status_code}"

    attrs = r.json()["data"]["attributes"]
    stats = attrs.get("last_analysis_stats", {})

    malicious  = stats.get("malicious", 0)
    suspicious = stats.get("suspicious", 0)
    harmless   = stats.get("harmless", 0)
    reputation = attrs.get("reputation", 0)

    # Categories: dict of {vendor: category} — collect unique category names
    categories = attrs.get("categories", {}) or {}
    unique_cats = sorted(set(categories.values()))
    cats_str = ", ".join(unique_cats[:5]) if unique_cats else "Uncategorized"

    log_info(f"[VirusTotal] Domain {domain} → {malicious} malicious, reputation {reputation}")

    if malicious > 0:
        level = f"🔴 DANGER Boss! '{domain}' was flagged MALICIOUS by {malicious} engines"
    elif suspicious > 0:
        level = f"🟡 CAUTION Boss. '{domain}' was flagged suspicious by {suspicious} engines"
    elif reputation < 0:
        level = f"🟡 CAUTION Boss. '{domain}' has a negative community reputation score ({reputation})"
    else:
        level = f"🟢 SAFE Boss. '{domain}' looks clean ({harmless} engines report no issues)"

    return f"{level}.\nCategories: {cats_str}\nCommunity reputation score: {reputation}"


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

    file_path = file_path.strip().strip('"').strip("'")

    if not os.path.exists(file_path):
        return f"File not found Boss: {file_path}"

    if not os.path.isfile(file_path):
        return f"'{file_path}' is not a file Boss."

    try:
        # Calculate SHA256 hash
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        file_hash = sha256.hexdigest()

        headers = {"x-apikey": api_key}
        r, err = _vt_get(f"/files/{file_hash}", headers)
        if err:
            return err

        if r.status_code == 404:
            return (f"File not in VirusTotal database Boss "
                    f"(hash: {file_hash[:16]}...). It may be new/unique.")

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

    UPGRADE: first checks against a small local list of the most
    commonly leaked passwords (instant, offline, no API call). If it's
    one of those, Cracka warns immediately. Otherwise falls through to
    the HaveIBeenPwned k-anonymity API as before — only the first 5
    chars of the SHA1 hash are sent, the password itself NEVER leaves
    your computer. 100% free, no API key.

    Voice: 'check password' (then Cracka will ask for the password)
    """
    if not password:
        return "Please provide a password to check Boss."

    # UPGRADE: instant local pre-check against common password list
    if password.lower() in COMMON_PASSWORDS:
        return ("🔴 WARNING Boss! This is one of the most commonly used "
                "passwords in the world — it's guessed in seconds by "
                "attackers, regardless of breach history. Change it "
                "immediately!")

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

        # UPGRADE: basic strength feedback even when not breached
        strength_notes = []
        if len(password) < 8:
            strength_notes.append("it's quite short (under 8 characters)")
        if password.isalpha() or password.isdigit():
            strength_notes.append("it only uses letters or only digits, not a mix")

        if strength_notes:
            return (f"🟡 Not found in known breaches Boss, but "
                    f"{' and '.join(strength_notes)} — consider making it "
                    f"longer and more varied for better security.")

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
    Smart router — detects if target is a URL, IP, domain, or email
    and runs the appropriate check.
    Voice: 'threat check <url/ip/domain/email>'
    """
    target = target.strip()

    # Email check
    if "@" in target and "." in target.split("@")[-1]:
        return check_email_pwned(target)

    # IP address check (simple pattern: 4 numbers separated by dots)
    parts = target.split(".")
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        return check_ip_virustotal(target)

    # UPGRADE: bare domain (no scheme, no path) → domain reputation check
    # instead of URL check, since VT treats these differently and domain
    # reputation gives richer category info for "is this site safe?"
    bare = target.replace("https://", "").replace("http://", "")
    if "/" not in bare and "." in bare:
        return check_domain_virustotal(bare)

    # Otherwise treat as full URL
    return check_url_virustotal(target)