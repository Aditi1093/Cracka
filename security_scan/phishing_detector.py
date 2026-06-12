"""
security_scan/phishing_detector.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ML-POWERED PHISHING/MALWARE/DEFACEMENT DETECTOR — Cracka AI

Upgraded from the original heuristic-only scorer to a trained
Random Forest model (94%+ accuracy, 651K URL dataset, 4 classes:
Benign / Phishing / Malware / Defacement) — same approach as the
standalone "URL Phishing Detector — P07" project, adapted to fit
Cracka's existing voice-command interface unchanged.

PUBLIC API (unchanged — gui.py / ai_brain.py need NO changes):
    detect_phishing(url: str) -> str

Required files in this same security_scan/ folder:
    - phishing_features.py     (feature extraction, from features.py)
    - phishing_model.pkl       (trained Random Forest model)

If either file is missing, falls back automatically to the original
lightweight heuristic scorer (no crash, just less accurate).
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "phishing_model.pkl")

LABELS = {
    0: ("SAFE",       "🟢"),
    1: ("PHISHING",   "🔴"),
    2: ("MALWARE",    "☠️"),
    3: ("DEFACEMENT", "🟠"),
}

# ─────────────────────────────────────────────────────────────────────────────
# LAZY MODEL LOADING — model + feature extractor loaded once, on first use
# ─────────────────────────────────────────────────────────────────────────────
_model = None
_model_load_attempted = False
_model_load_error = None


def _try_load_model():
    """
    Load the trained ML model and feature extractor on first use.
    Sets _model_load_error if anything is missing, so detect_phishing()
    can fall back to the heuristic scorer without crashing.
    """
    global _model, _model_load_attempted, _model_load_error

    if _model_load_attempted:
        return

    _model_load_attempted = True

    try:
        import joblib
        from security_scan.phishing_features import extract_features, is_trusted
    except ImportError as e:
        _model_load_error = f"phishing_features.py not found or import error: {e}"
        return

    if not os.path.exists(MODEL_PATH):
        _model_load_error = "phishing_model.pkl not found in security_scan/"
        return

    try:
        _model = joblib.load(MODEL_PATH)
    except Exception as e:
        _model_load_error = f"Could not load phishing_model.pkl: {e}"
        _model = None


# ─────────────────────────────────────────────────────────────────────────────
# ML-BASED DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _detect_phishing_ml(url: str) -> str:
    """
    ML-based detection using the trained Random Forest model.
    Returns a Cracka-style result string with emoji + Boss tone.
    """
    import pandas as pd
    from security_scan.phishing_features import extract_features, is_trusted

    features = extract_features(url)
    X = pd.DataFrame([features])

    prediction = _model.predict(X)[0]
    proba = _model.predict_proba(X)[0]
    confidence = round(max(proba) * 100, 2)

    # Trusted-domain override — if the domain is a well-known major site
    # but the model flagged it, trust the whitelist instead.
    override = False
    if is_trusted(url) and prediction != 0:
        prediction = 0
        confidence = 99.0
        override = True

    label, emoji = LABELS[prediction]

    result = f"{emoji} {label} (confidence: {confidence}%)"

    if label != "SAFE":
        details = []
        if features.get("has_ip"):
            details.append("uses a raw IP address")
        if features.get("has_suspicious_tld"):
            details.append("suspicious top-level domain")
        if features.get("suspicious_word_count", 0) > 0:
            details.append(f"{features['suspicious_word_count']} suspicious keyword(s)")
        if features.get("has_at_symbol"):
            details.append("contains '@' redirection trick")
        if features.get("subdomain_count", 0) > 2:
            details.append(f"{features['subdomain_count']} subdomains")
        if not features.get("is_https"):
            details.append("not using HTTPS")

        if details:
            result += "\nReasons: " + "; ".join(details)

    if override:
        result += "\n(ℹ️ Trusted domain override applied — recognized as a major site)"

    return result


# ─────────────────────────────────────────────────────────────────────────────
# HEURISTIC FALLBACK — original Cracka logic, used if ML model unavailable
# ─────────────────────────────────────────────────────────────────────────────

def _detect_phishing_heuristic(url: str) -> str:
    """
    Original heuristic-based scorer (kept as a safety net so Cracka
    never crashes if the ML model files aren't present, e.g. before
    first-time setup or if phishing_model.pkl wasn't copied over).
    """
    url_low = url.strip().lower()
    score = 0
    reasons = []

    if url_low.startswith("http://"):
        score += 2
        reasons.append("Uses HTTP (not secure)")

    if re.search(r"\d+\.\d+\.\d+\.\d+", url_low):
        score += 3
        reasons.append("Uses raw IP address (no domain name)")

    suspicious_words = [
        "login", "verify", "update", "secure", "bank", "account",
        "password", "confirm", "paypal", "signin", "wallet",
        "free", "prize", "winner", "click", "urgent", "suspended"
    ]
    found = [w for w in suspicious_words if w in url_low]
    if found:
        score += len(found)
        reasons.append(f"Suspicious keywords: {', '.join(found[:3])}")

    try:
        domain = re.sub(r"^https?://", "", url_low).split("/")[0]
        domain = domain.split("@")[-1].split(":")[0]
        parts = [p for p in domain.split(".") if p]
        subdomain_count = max(0, len(parts) - 2)
        if subdomain_count > 2:
            score += 2
            reasons.append(f"Too many subdomains ({subdomain_count})")
    except Exception:
        pass

    if len(url_low) > 100:
        score += 1
        reasons.append(f"Unusually long URL ({len(url_low)} chars)")

    if "@" in url_low:
        score += 2
        reasons.append("Contains '@' in URL (redirection trick)")

    scheme_stripped = re.sub(r"^https?://", "", url_low)
    if "//" in scheme_stripped:
        score += 1
        reasons.append("Unexpected '//' after domain (possible open redirect)")

    typosquat = {
        "paypa1": "paypal", "g00gle": "google", "facebok": "facebook",
        "arnazon": "amazon", "micros0ft": "microsoft", "gogle": "google"
    }
    for fake, real in typosquat.items():
        if fake in url_low:
            score += 4
            reasons.append(f"Possible typosquatting of '{real}'")

    if score >= 6:
        level, emoji = "HIGH PHISHING RISK", "🔴"
    elif score >= 3:
        level, emoji = "MEDIUM RISK", "🟡"
    elif score >= 1:
        level, emoji = "LOW RISK", "🟠"
    else:
        level, emoji = "SAFE", "🟢"

    result = f"{emoji} {level} (score: {score}) [heuristic mode]"
    if reasons:
        result += "\nReasons: " + "; ".join(reasons)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API — same signature as before, ai_brain.py / gui.py unchanged
# ─────────────────────────────────────────────────────────────────────────────

def detect_phishing(url: str) -> str:
    """
    Analyze a URL for phishing/malware/defacement indicators.
    Voice: 'phishing check <url>'

    Tries the trained ML model first (94%+ accuracy on 651K-URL
    dataset, 4-class: Benign/Phishing/Malware/Defacement). Falls back
    to the original heuristic scorer if the model files aren't
    present — never crashes either way.
    """
    if not url or not url.strip():
        return "Please say the URL Boss."

    url = url.strip()

    _try_load_model()

    if _model is not None:
        try:
            return _detect_phishing_ml(url)
        except Exception as e:
            # Don't crash on unexpected ML errors — fall back gracefully
            return _detect_phishing_heuristic(url) + f"\n(ML error, used fallback: {e})"

    # Model unavailable — heuristic fallback
    note = f" ({_model_load_error})" if _model_load_error else ""
    return _detect_phishing_heuristic(url)