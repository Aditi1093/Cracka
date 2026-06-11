"""
╔══════════════════════════════════════════╗
║     CRACKA AI — CVE SCANNER              ║
║   security_scan/cve_scanner.py           ║
║   Checks software for known              ║
║   vulnerabilities (CVEs) using NVD       ║
╚══════════════════════════════════════════╝

Uses: NVD (National Vulnerability Database) — US Govt, FREE
  https://nvd.nist.gov/developers/vulnerabilities

No API key required, but rate-limited:
  - Without key: 5 requests / 30 seconds
  - With key:    50 requests / 30 seconds (free, instant)
  Get key: https://nvd.nist.gov/developers/request-an-api-key
  Add to data/credentials.json as "nvd_api_key"
"""

import os
import json
import time
import requests
from core.logger import log_info, log_error

CREDENTIALS_FILE = "data/credentials.json"
NVD_API_URL      = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Software we commonly check on Boss's PC — keyword used for NVD search
COMMON_SOFTWARE = [
    "Google Chrome",
    "Mozilla Firefox",
    "Microsoft Edge",
    "VLC media player",
    "7-Zip",
    "Zoom",
    "Python",
]

# Severity emoji mapping
SEVERITY_EMOJI = {
    "CRITICAL": "🔴",
    "HIGH":     "🟠",
    "MEDIUM":   "🟡",
    "LOW":      "🟢",
}


# ─────────────────────────────────────────────────────────────────────────────
# CREDENTIALS HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _get_nvd_api_key() -> str:
    """Get NVD API key from environment or credentials.json (optional)."""
    key = os.environ.get("NVD_API_KEY", "").strip()
    if key:
        return key
    try:
        if os.path.exists(CREDENTIALS_FILE):
            with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
                creds = json.load(f)
            return creds.get("nvd_api_key", "").strip()
    except Exception as e:
        log_error(f"[CVEScanner] Could not read {CREDENTIALS_FILE}: {e}")
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# GET INSTALLED SOFTWARE (Windows Registry)
# ─────────────────────────────────────────────────────────────────────────────

def get_installed_software(limit: int = 30) -> list:
    """
    Read installed programs from Windows Registry.
    Returns list of dicts: [{"name": ..., "version": ...}, ...]
    """
    software = []

    try:
        import winreg

        # Check both 64-bit and 32-bit registry locations
        registry_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER,  r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]

        seen = set()

        for hive, path in registry_paths:
            try:
                key = winreg.OpenKey(hive, path)
            except FileNotFoundError:
                continue

            for i in range(winreg.QueryInfoKey(key)[0]):
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    subkey = winreg.OpenKey(key, subkey_name)

                    name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                    try:
                        version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                    except FileNotFoundError:
                        version = "Unknown"

                    if name and name not in seen:
                        seen.add(name)
                        software.append({"name": name, "version": version})

                except (FileNotFoundError, OSError):
                    continue

            winreg.CloseKey(key)

        # Sort alphabetically
        software.sort(key=lambda x: x["name"].lower())
        return software[:limit]

    except ImportError:
        log_error("[CVEScanner] winreg not available — not on Windows?")
        return []
    except Exception as e:
        log_error(f"[CVEScanner] Registry read error: {e}")
        return []


def list_installed_software() -> str:
    """
    Voice command: 'list installed software'
    Returns a readable list of installed programs.
    """
    software = get_installed_software(limit=20)

    if not software:
        return "Could not read installed software Boss. This feature works on Windows only."

    lines = [f"Installed software Boss ({len(software)} shown):"]
    for s in software:
        lines.append(f"  • {s['name']} (v{s['version']})")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# NVD API — SEARCH CVEs
# ─────────────────────────────────────────────────────────────────────────────

def search_cves(keyword: str, max_results: int = 5) -> str:
    """
    Search NVD for CVEs matching a keyword (software name).
    Voice: 'check vulnerabilities for chrome' / 'cve check python'
    """
    if not keyword or not keyword.strip():
        return "Please tell me which software to check Boss."

    keyword = keyword.strip()

    # FIX: NVD's servers (Akamai WAF) often return 404 for requests
    # with the default python-requests User-Agent. Adding a real
    # User-Agent header fixes this.
    headers = {
        "User-Agent": "Mozilla/5.0 (Cracka-AI-Security-Scanner/1.0)"
    }

    api_key = _get_nvd_api_key()
    if api_key:
        headers["apiKey"] = api_key

    try:
        params = {
            "keywordSearch": keyword,
            "resultsPerPage": max_results,
        }

        r = requests.get(NVD_API_URL, headers=headers, params=params, timeout=15)

        if r.status_code == 403:
            return "NVD rate limit hit Boss. Please wait 30 seconds and try again."

        if r.status_code == 404:
            return ("NVD service returned 404 Boss — this can happen if "
                    "their server is temporarily blocking the request. "
                    "Please try again in a few seconds.")

        if r.status_code != 200:
            return f"NVD error Boss. Status: {r.status_code}"

        data        = r.json()
        total       = data.get("totalResults", 0)
        items       = data.get("vulnerabilities", [])

        if total == 0 or not items:
            return f"🟢 No known CVEs found for '{keyword}' Boss. Looks safe!"

        lines = [f"Found {total} CVE(s) for '{keyword}' Boss. Top {len(items)}:"]

        for item in items:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "Unknown")

            # Get English description
            descriptions = cve.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")
            desc_short = (desc[:120] + "...") if len(desc) > 120 else desc

            # Get severity (try v3.1, then v3.0, then v2)
            severity = "UNKNOWN"
            score    = "N/A"
            metrics  = cve.get("metrics", {})

            for metric_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                if metric_key in metrics and metrics[metric_key]:
                    cvss_data = metrics[metric_key][0].get("cvssData", {})
                    severity  = cvss_data.get("baseSeverity",
                                metrics[metric_key][0].get("baseSeverity", "UNKNOWN"))
                    score     = cvss_data.get("baseScore", "N/A")
                    break

            emoji = SEVERITY_EMOJI.get(severity.upper(), "⚪")

            lines.append(f"\n{emoji} {cve_id} — {severity} (score: {score})")
            lines.append(f"   {desc_short}")

        log_info(f"[CVEScanner] Found {total} CVEs for '{keyword}'")
        return "\n".join(lines)

    except requests.exceptions.Timeout:
        return "NVD request timed out Boss. Please try again."
    except Exception as e:
        log_error(f"[CVEScanner] Search error: {e}")
        return f"Could not check vulnerabilities Boss: {e}"


def check_software_cve(command: str) -> str:
    """
    Parse software name from voice command and check CVEs.
    Voice: 'check vulnerabilities for chrome'
           'cve check python'
           'is firefox vulnerable'
    """
    cmd = command.lower()

    # Remove trigger phrases to extract software name
    for phrase in [
        "check vulnerabilities for", "check vulnerability for",
        "cve check", "cve scan", "is", "vulnerable",
        "vulnerabilities for", "vulnerability for",
        "check cve for", "check cve",
    ]:
        cmd = cmd.replace(phrase, "")

    software = cmd.strip()

    if not software:
        return "Please tell me which software to check Boss. Example: 'check vulnerabilities for chrome'."

    return search_cves(software, max_results=5)


# ─────────────────────────────────────────────────────────────────────────────
# FULL SYSTEM SCAN
# ─────────────────────────────────────────────────────────────────────────────

def scan_installed_software(limit: int = 5) -> str:
    """
    Voice command: 'scan my software' / 'scan installed programs for vulnerabilities'
    Checks the most important installed software against NVD.
    Limited to `limit` programs to respect NVD rate limits (5 req / 30 sec).
    """
    installed = get_installed_software(limit=50)

    if not installed:
        return "Could not read installed software Boss. This feature works on Windows only."

    # Match installed software against our common-software watchlist
    installed_names = {s["name"].lower(): s for s in installed}

    targets = []
    for common in COMMON_SOFTWARE:
        for name_lower, info in installed_names.items():
            if common.lower().split()[0] in name_lower:
                targets.append(info)
                break

    if not targets:
        return ("Could not match any common software Boss. "
                "Try 'check vulnerabilities for <software name>' instead.")

    targets = targets[:limit]

    has_api_key = bool(_get_nvd_api_key())
    delay = 0 if has_api_key else 6  # NVD free tier: 5 req / 30 sec ≈ 6 sec gap

    results = []
    high_risk_found = []

    for i, sw in enumerate(targets):
        if i > 0 and delay:
            time.sleep(delay)

        cve_summary = search_cves(sw["name"], max_results=1)

        if "🔴" in cve_summary or "🟠" in cve_summary:
            high_risk_found.append(sw["name"])

        results.append(f"• {sw['name']} (v{sw['version']})")

    log_info(f"[CVEScanner] Scanned {len(targets)} programs, "
             f"{len(high_risk_found)} with high/critical CVEs")

    summary = [f"Scanned {len(targets)} programs Boss:"]
    summary.extend(results)

    if high_risk_found:
        summary.append(f"\n🔴 WARNING! These have HIGH/CRITICAL vulnerabilities:")
        for name in high_risk_found:
            summary.append(f"  ⚠️ {name}")
        summary.append("\nSay 'check vulnerabilities for <name>' for details.")
    else:
        summary.append("\n🟢 No critical vulnerabilities found in scanned software!")

    if not has_api_key:
        summary.append(
            "\n(Tip: Add a free NVD API key to data/credentials.json "
            "for faster, more thorough scans — nvd.nist.gov/developers/request-an-api-key)"
        )

    return "\n".join(summary)