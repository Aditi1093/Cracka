"""
╔══════════════════════════════════════════╗
║         CRACKA AI — TRANSLATOR           ║
║   utils/translator.py                    ║
║   Full multilingual layer: translation,  ║
║   language detection, auto-translate     ║
║   mode for Cracka's responses.           ║
╚══════════════════════════════════════════╝

Uses deep_translator (free, no API key):
    pip install deep-translator

PUBLIC API:
    translate_text(command)        → handle 'translate X to Y' commands
    translate_to(text, target)     → low-level: translate text to target lang
    detect_language(text)          → guess source language of text
    list_supported_languages()     → voice: "what languages can you translate"
    set_preferred_language(cmd)    → voice: "talk to me in hindi" / "reply in english"
    get_preferred_language()       → used by ai_brain to auto-translate ALL responses
    clear_preferred_language()     → voice: "stop translating" / "speak english only"
    wrap_response(text)            → auto-translates any Cracka response if a
                                      preferred language is set (called from ai_brain)

CHANGES FROM ORIGINAL:
  1. FIX: word-removal bug — "translate together to hindi" no longer
     corrupts "together" into "gether". Uses regex word-boundaries
     instead of naive .replace().
  2. NEW: source language support — "translate namaste from hindi to
     english" now works (previously source was always "auto").
  3. NEW: reverse/definition phrasing — "what does bonjour mean in
     english" / "what does namaste mean".
  4. NEW: list_supported_languages() — "what languages do you support".
  5. NEW: persistent language preference — "talk to me in hindi" sets
     a session-wide output language; ai_brain can call wrap_response()
     on EVERY response so the whole assistant becomes multilingual
     with one hook, not just the translate command.
  6. NEW: detect_language() — "what language is this: <text>".
  7. Expanded LANG_CODES (30+ languages incl. Bengali, Urdu, Punjabi,
     Malayalam, Kannada, Vietnamese, Thai, Turkish, Polish, Dutch).
  8. All functions degrade gracefully if deep_translator isn't
     installed — return a helpful install message, never crash.
"""

import re
from core.logger import log_info, log_error

# ─────────────────────────────────────────────────────────────────────────────
# LANGUAGE TABLE — name → ISO code (expanded)
# ─────────────────────────────────────────────────────────────────────────────
LANG_CODES = {
    "english":    "en",
    "hindi":      "hi",
    "marathi":    "mr",
    "french":     "fr",
    "spanish":    "es",
    "german":     "de",
    "japanese":   "ja",
    "chinese":    "zh-CN",
    "mandarin":   "zh-CN",
    "arabic":     "ar",
    "portuguese": "pt",
    "russian":    "ru",
    "italian":    "it",
    "korean":     "ko",
    "gujarati":   "gu",
    "tamil":      "ta",
    "telugu":     "te",
    "bengali":    "bn",
    "punjabi":    "pa",
    "urdu":       "ur",
    "malayalam":  "ml",
    "kannada":    "kn",
    "odia":       "or",
    "vietnamese": "vi",
    "thai":       "th",
    "turkish":    "tr",
    "polish":     "pl",
    "dutch":      "nl",
    "greek":      "el",
    "hebrew":     "iw",
    "indonesian": "id",
    "swahili":    "sw",
    "ukrainian":  "uk",
    "persian":    "fa",
    "farsi":      "fa",
}

# Reverse map: code → display name (for friendly responses)
CODE_TO_NAME = {v: k for k, v in LANG_CODES.items()}
# Prefer nicer display names for duplicate codes
CODE_TO_NAME["zh-CN"] = "chinese"
CODE_TO_NAME["fa"] = "persian"

# Words to strip when extracting the text-to-translate.
# Longer phrases listed first so regex matches greedily / correctly.
FILLER_PHRASES = [
    "please translate", "can you translate", "translate this",
    "translate", "what does", "how do you say", "how to say",
    "say", "mean in", "means in", "mean", "means",
    "from", "into", "in", "to",
]


# ─────────────────────────────────────────────────────────────────────────────
# SESSION-WIDE PREFERRED LANGUAGE
# Stored in a small in-memory dict (per-process). For multi-user setups
# this could be moved into SessionMemory, but Cracka is single-user.
# ─────────────────────────────────────────────────────────────────────────────
_preferred_language = {"code": None, "name": None}


def get_preferred_language() -> str:
    """Returns the current preferred output language code, or None."""
    return _preferred_language["code"]


def set_preferred_language(command: str) -> str:
    """
    Voice: 'talk to me in hindi' / 'reply in french' /
           'switch to spanish' / 'speak in marathi'

    Sets a session-wide preferred output language. After this,
    ai_brain.process() should call wrap_response() on every response
    so ALL of Cracka's replies get auto-translated — not just the
    'translate' command.
    """
    cmd = command.lower()

    for lang_name, code in LANG_CODES.items():
        if lang_name in cmd:
            _preferred_language["code"] = code
            _preferred_language["name"] = lang_name
            log_info(f"[Translator] Preferred language set to {lang_name} ({code})")

            if code == "en":
                return "Okay Boss, I'll reply in English from now on."

            # Confirm in the NEW language too, so Boss immediately sees it working
            confirmation = f"Okay Boss, I'll reply in {lang_name.title()} from now on."
            translated = translate_to(confirmation, code)
            return translated or confirmation

    return ("Please tell me which language Boss — for example "
            "'talk to me in Hindi' or 'reply in Spanish'.")


def clear_preferred_language() -> str:
    """
    Voice: 'stop translating' / 'speak english only' /
           'reset language' / 'talk to me normally'
    """
    had_pref = _preferred_language["code"] is not None
    _preferred_language["code"] = None
    _preferred_language["name"] = None
    log_info("[Translator] Preferred language cleared")

    if had_pref:
        return "Okay Boss, back to English."
    return "I was already replying in English Boss."


def wrap_response(text: str) -> str:
    """
    Called from ai_brain.process() on the FINAL response, right before
    returning it. If Boss has set a preferred language (via
    set_preferred_language), every response gets auto-translated into
    that language. If no preference is set, returns text unchanged
    (zero overhead).

    This is the "one hook makes everything multilingual" piece —
    security scan results, CVE reports, jokes, weather, etc. all pass
    through here.

    Usage in ai_brain.py, at the very end of process():
        result = <whatever was computed above>
        return translator.wrap_response(result)
    """
    code = _preferred_language["code"]
    if not code or code == "en" or not text:
        return text

    translated = translate_to(text, code)
    return translated if translated is not None else text


# ─────────────────────────────────────────────────────────────────────────────
# LOW-LEVEL TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────

def translate_to(text: str, target_code: str, source_code: str = "auto") -> str:
    """
    Translate `text` to `target_code` (ISO language code).
    Returns None on failure (caller should handle fallback) rather
    than raising, so wrap_response() can fail silently and return
    the original English text.

    NOTE: deep_translator's GoogleTranslator has a per-request
    character limit (~5000 chars via the free web endpoint). Long
    Cracka responses (e.g. CVE scan reports with many lines) are
    chunked by line to stay under this safely and to avoid a single
    failed long string discarding the whole translation.
    """
    if not text or not text.strip():
        return text

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        log_error("[Translator] deep_translator not installed")
        return None

    try:
        translator = GoogleTranslator(source=source_code, target=target_code)

        # Chunk by line for long multi-line responses (security reports,
        # CVE lists, etc.) — keeps each request small and means a
        # failure on one line doesn't lose the whole translation.
        lines = text.split("\n")
        translated_lines = []

        for line in lines:
            if not line.strip():
                translated_lines.append(line)
                continue
            try:
                translated_lines.append(translator.translate(line))
            except Exception as e:
                log_error(f"[Translator] Line translation failed, keeping original: {e}")
                translated_lines.append(line)

        return "\n".join(translated_lines)

    except Exception as e:
        log_error(f"[Translator] Translation error: {e}")
        return None


def detect_language(text: str) -> str:
    """
    Voice: 'what language is this <text>' / 'detect language <text>'

    Best-effort source language detection. deep_translator doesn't
    have a dedicated detect API across all backends, so this uses a
    translate-to-English round trip via GoogleTranslator with
    source='auto' and reads back the detected source language when
    available; falls back to a simple script-based heuristic for
    common cases (Devanagari, Arabic script, CJK) if that fails.
    """
    if not text or not text.strip():
        return "Please give me some text to check Boss."

    text = text.strip()

    # Quick script-based heuristic first (fast, offline, no API call)
    if re.search(r"[\u0900-\u097F]", text):
        return "That looks like Devanagari script Boss — likely Hindi or Marathi."
    if re.search(r"[\u0600-\u06FF]", text):
        return "That looks like Arabic script Boss — could be Arabic, Urdu, or Persian."
    if re.search(r"[\u4e00-\u9fff]", text):
        return "That looks like Chinese script Boss."
    if re.search(r"[\u3040-\u30ff]", text):
        return "That looks like Japanese script Boss (Hiragana/Katakana)."
    if re.search(r"[\uac00-\ud7a3]", text):
        return "That looks like Korean script Boss (Hangul)."
    if re.search(r"[\u0e00-\u0e7f]", text):
        return "That looks like Thai script Boss."

    # Fall back to translation library's language detection, if available
    try:
        from deep_translator import single_detection
        # single_detection needs an API key for some backends; wrap safely
        detected = single_detection(text, api_key=None)
        name = CODE_TO_NAME.get(detected, detected)
        return f"That looks like {name.title()} Boss (code: {detected})."
    except Exception:
        pass

    return ("I think that's Latin-script text Boss (English or a European "
            "language) — I can't pin down the exact language without more "
            "context.")


def list_supported_languages() -> str:
    """
    Voice: 'what languages can you translate' /
           'what languages do you support' / 'list languages'
    """
    names = sorted(set(CODE_TO_NAME.values()))
    formatted = ", ".join(n.title() for n in names)
    return (f"I can translate to/from {len(names)} languages Boss, "
            f"including: {formatted}.")


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND PARSING — "translate X to Y [from Z]"
# ─────────────────────────────────────────────────────────────────────────────

def _find_language_in(text: str):
    """
    Find the FIRST language name in `text` as a whole word.
    Returns (lang_name, code, span) or (None, None, None).
    Uses word-boundary regex so 'spanish' inside another word
    wouldn't match — and longer names are checked first so e.g.
    'portuguese' isn't accidentally matched as part of something else.
    """
    # Check longer language names first to avoid partial overlaps
    for lang_name in sorted(LANG_CODES.keys(), key=len, reverse=True):
        pattern = r"\b" + re.escape(lang_name) + r"\b"
        match = re.search(pattern, text)
        if match:
            return lang_name, LANG_CODES[lang_name], match.span()
    return None, None, None


def _strip_word(text: str, word: str) -> str:
    """Remove a whole word/phrase from text using word boundaries
    (FIX for the original .replace() substring bug)."""
    pattern = r"\b" + re.escape(word) + r"\b"
    return re.sub(pattern, " ", text)


def translate_text(command: str) -> str:
    """
    Translate text based on a voice command. Supports several phrasings:

        'translate hello to hindi'
        'translate namaste from hindi to english'
        'how do you say good morning in french'
        'what does bonjour mean'                  (→ translate to English)
        'what does bonjour mean in spanish'       (→ translate to Spanish)

    FIX: previously used naive `.replace()` on filler words, which
    could corrupt the text if a filler word appeared as a substring
    inside it (e.g. "together" contains "to" → became "gether").
    Now uses word-boundary regex throughout.
    """
    original = command.strip()
    cmd = command.lower().strip()

    if not cmd:
        return "Please tell me what to translate Boss."

    # ── "what does X mean [in Y]" — reverse/definition phrasing ──────────
    define_match = re.search(
        r"what does (.+?) mean(?: in (\w+))?$", cmd
    )
    if define_match:
        text_to_translate = define_match.group(1).strip()
        target_lang_name = define_match.group(2)
        target_code = LANG_CODES.get(target_lang_name, "en") if target_lang_name else "en"

        translated = translate_to(text_to_translate, target_code)
        if translated is None:
            return "Please install deep_translator: pip install deep-translator"

        target_display = CODE_TO_NAME.get(target_code, "english").title()
        return f"'{text_to_translate}' means '{translated}' in {target_display}."

    # ── "translate X from Y to Z" or "translate X to Y" ──────────────────
    target_lang_name, target_code, target_span = None, None, None
    source_lang_name, source_code, source_span = None, None, None

    # Look for "to <language>" near the end (target language)
    to_match = re.search(r"\bto\s+(\w+)\b", cmd)
    if to_match and to_match.group(1) in LANG_CODES:
        target_lang_name = to_match.group(1)
        target_code = LANG_CODES[target_lang_name]
        target_span = to_match.span()

    # Look for "from <language>" (source language)
    from_match = re.search(r"\bfrom\s+(\w+)\b", cmd)
    if from_match and from_match.group(1) in LANG_CODES:
        source_lang_name = from_match.group(1)
        source_code = LANG_CODES[source_lang_name]
        source_span = from_match.span()

    # Also support "in <language>" as target if "to" form wasn't found
    # e.g. "how do you say good morning in french"
    if target_code is None:
        in_match = re.search(r"\bin\s+(\w+)\b", cmd)
        if in_match and in_match.group(1) in LANG_CODES:
            target_lang_name = in_match.group(1)
            target_code = LANG_CODES[target_lang_name]
            target_span = in_match.span()

    if target_code is None:
        target_code = "hi"  # default to Hindi, as in the original
        target_lang_name = "hindi"

    # ── Extract the actual text to translate ─────────────────────────────
    # Remove the matched language spans first (by position, to avoid
    # accidentally stripping a language NAME that's part of the
    # content itself — e.g. "translate I love French food to hindi").
    spans_to_remove = [s for s in (target_span, source_span) if s]
    # Remove from rightmost to leftmost so earlier indices stay valid
    spans_to_remove.sort(key=lambda s: s[0], reverse=True)

    working = cmd
    for start, end in spans_to_remove:
        working = working[:start] + " " + working[end:]

    # Now strip filler/command words using WORD-BOUNDARY regex
    # (the original bug: naive .replace("to", "") on substrings)
    for phrase in [
        "please translate", "can you translate", "translate this",
        "translate", "how do you say", "how to say", "say",
    ]:
        working = re.sub(r"\b" + re.escape(phrase) + r"\b", " ", working)

    text = re.sub(r"\s+", " ", working).strip()

    if not text:
        return "Please tell me what you want to translate Boss."

    translated = translate_to(text, target_code, source_code or "auto")

    if translated is None:
        return "Please install deep_translator: pip install deep-translator"

    target_display = CODE_TO_NAME.get(target_code, target_code).title()
    log_info(f"[Translator] '{text}' → {target_display}: '{translated}'")

    if source_code:
        source_display = CODE_TO_NAME.get(source_code, source_code).title()
        return f"'{text}' ({source_display}) in {target_display}: {translated}"

    return f"In {target_display}: {translated}"