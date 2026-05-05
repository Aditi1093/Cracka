"""
security_scan/phishing_detector.py
URL phishing detection using heuristic scoring.
"""

import re
import socket


def detect_phishing(url: str) -> str:
    """
    Analyze a URL for phishing indicators.
    Returns risk level with explanation.
    """
    url = url.strip().lower()
    score = 0
    reasons = []

    # 1. HTTP instead of HTTPS
    if url.startswith("http://"):
        score += 2
        reasons.append("Uses HTTP (not secure)")

    # 2. IP address instead of domain
    if re.search(r"\d+\.\d+\.\d+\.\d+", url):
        score += 3
        reasons.append("Uses raw IP address (no domain name)")

    # 3. Suspicious keywords in URL
    suspicious_words = [
        "login", "verify", "update", "secure", "bank", "account",
        "password", "confirm", "paypal", "signin", "wallet",
        "free", "prize", "winner", "click", "urgent", "suspended"
    ]
    found = [w for w in suspicious_words if w in url]
    if found:
        score += len(found)
        reasons.append(f"Suspicious keywords: {', '.join(found[:3])}")

    # 4. Too many subdomains
    try:
        domain = re.sub(r"https?://", "", url).split("/")[0]
        subdomain_count = domain.count(".")
        if subdomain_count > 3:
            score += 2
            reasons.append(f"Too many subdomains ({subdomain_count})")
    except Exception:
        pass

    # 5. Very long URL
    if len(url) > 100:
        score += 1
        reasons.append(f"Unusually long URL ({len(url)} chars)")

    # 6. Special characters (encoded attacks)
    if "@" in url:
        score += 2
        reasons.append("Contains '@' in URL (redirection trick)")
    if "//" in url.replace("://", ""):
        score += 1
        reasons.append("Double slashes (suspicious redirect)")

    # 7. Typosquatting check (common brands misspelled)
    typosquat = {
        "paypa1": "paypal", "g00gle": "google", "facebok": "facebook",
        "arnazon": "amazon", "micros0ft": "microsoft", "gogle": "google"
    }
    for fake, real in typosquat.items():
        if fake in url:
            score += 4
            reasons.append(f"Possible typosquatting of '{real}'")

    # 8. Domain age (basic check — requires whois)
    # Skipped for speed

    # Build result
    if score >= 6:
        level = "HIGH PHISHING RISK"
        emoji = "🔴"
    elif score >= 3:
        level = "MEDIUM RISK"
        emoji = "🟡"
    elif score >= 1:
        level = "LOW RISK"
        emoji = "🟠"
    else:
        level = "SAFE"
        emoji = "🟢"

    result = f"{emoji} {level} (score: {score})"
    if reasons:
        result += "\nReasons: " + "; ".join(reasons)
    return result