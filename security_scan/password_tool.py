"""
╔══════════════════════════════════════════╗
║   CRACKA AI — PASSWORD TOOL              ║
║   security_scan/password_tool.py         ║
║   Generates strong passwords and rates   ║
║   password strength.                     ║
╚══════════════════════════════════════════╝

Complements threat_intelligence.py:
  - threat_intelligence.check_password_pwned() → "has this leaked?"
  - this module                                 → "how strong is it?"
                                                   and "give me a strong one"

No external APIs — fully offline, instant.
"""

import re
import math
import random
import string
from core.logger import log_info

# Words to avoid as building blocks (case-insensitive substring match)
COMMON_WORDS = {
    "password", "qwerty", "admin", "welcome", "letmein", "login",
    "iloveyou", "dragon", "monkey", "football", "princess", "starwars",
}

AMBIGUOUS_CHARS = "0O1lI"  # often confused when typed/read


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_password(length: int = 16, exclude_ambiguous: bool = True,
                       use_symbols: bool = True) -> str:
    """
    Generate a cryptographically random password.
    Guarantees at least one lowercase, uppercase, digit, and symbol
    (if enabled) for a length >= 4.
    """
    length = max(8, min(length, 128))

    lowers  = string.ascii_lowercase
    uppers  = string.ascii_uppercase
    digits  = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if exclude_ambiguous:
        lowers  = "".join(c for c in lowers if c not in AMBIGUOUS_CHARS)
        uppers  = "".join(c for c in uppers if c not in AMBIGUOUS_CHARS)
        digits  = "".join(c for c in digits if c not in AMBIGUOUS_CHARS)

    pools = [lowers, uppers, digits]
    if use_symbols:
        pools.append(symbols)

    all_chars = "".join(pools)
    rng = random.SystemRandom()  # cryptographically secure

    # Guarantee at least one char from each pool
    password_chars = [rng.choice(pool) for pool in pools]
    remaining = length - len(password_chars)
    password_chars += [rng.choice(all_chars) for _ in range(remaining)]

    rng.shuffle(password_chars)
    return "".join(password_chars)


def generate_passphrase(num_words: int = 4) -> str:
    """
    Generate a memorable passphrase (word1-word2-word3-Number).
    Easier to remember/speak aloud than a random string, while still
    being strong due to length and word-combination entropy.
    """
    # Small built-in wordlist — enough variety for a demo/personal tool
    words = [
        "river", "mountain", "tiger", "ocean", "forest", "rocket", "shadow",
        "ember", "crystal", "thunder", "falcon", "meadow", "comet", "lantern",
        "horizon", "whisper", "granite", "marble", "velvet", "copper",
        "willow", "phoenix", "harbor", "glacier", "cobalt", "amber",
        "quartz", "raven", "summit", "echo", "drift", "spark", "orbit",
    ]

    rng = random.SystemRandom()
    chosen = [rng.choice(words).capitalize() for _ in range(max(2, num_words))]
    number = rng.randint(10, 99)
    symbol = rng.choice("!@#$%&*")

    return "-".join(chosen) + str(number) + symbol


def generate_password_voice(command: str = "") -> str:
    """
    Voice: 'generate password' / 'create a strong password' /
           'generate passphrase' / 'make a memorable password'
    """
    cmd = command.lower()

    if "passphrase" in cmd or "memorable" in cmd or "easy to remember" in cmd:
        pw = generate_passphrase()
        log_info("[PasswordTool] Generated passphrase")
        return (f"Here's a memorable passphrase Boss:\n\n{pw}\n\n"
                f"It's strong because of its length and word combination — "
                f"store it in a password manager, don't reuse it.")

    # Extract length if mentioned, e.g. "generate password 20 characters"
    length_match = re.search(r"(\d+)", cmd)
    length = int(length_match.group(1)) if length_match else 16
    length = max(8, min(length, 64))

    pw = generate_password(length=length)
    log_info(f"[PasswordTool] Generated {length}-char password")

    return (f"Here's a strong {length}-character password Boss:\n\n{pw}\n\n"
            f"Save it in a password manager — Cracka does not store this.")


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD STRENGTH CHECKER (offline, entropy-based)
# ─────────────────────────────────────────────────────────────────────────────

def _estimate_entropy_bits(password: str) -> float:
    """
    Rough entropy estimate: log2(pool_size) * length.
    Pool size depends on which character classes are present.
    This is a heuristic, not a substitute for breach-database checks.
    """
    pool = 0
    if re.search(r"[a-z]", password):
        pool += 26
    if re.search(r"[A-Z]", password):
        pool += 26
    if re.search(r"[0-9]", password):
        pool += 10
    if re.search(r"[^a-zA-Z0-9]", password):
        pool += 32

    pool = max(pool, 1)
    return len(password) * math.log2(pool)


def check_password_strength(password: str) -> str:
    """
    Voice: 'how strong is my password' / 'check password strength'

    Offline strength rating based on length, character variety, and
    common-pattern detection. For breach-database checking, use
    threat_intelligence.check_password_pwned() instead — the two are
    complementary (this answers "how strong", that answers "has it leaked").
    """
    if not password:
        return "Please provide a password to check Boss."

    issues = []
    pw_lower = password.lower()

    # Length
    if len(password) < 8:
        issues.append("too short (under 8 characters)")
    elif len(password) < 12:
        issues.append("a bit short — 12+ characters recommended")

    # Character variety
    has_lower = bool(re.search(r"[a-z]", password))
    has_upper = bool(re.search(r"[A-Z]", password))
    has_digit = bool(re.search(r"[0-9]", password))
    has_symbol = bool(re.search(r"[^a-zA-Z0-9]", password))

    variety = sum([has_lower, has_upper, has_digit, has_symbol])
    if variety < 3:
        missing = []
        if not has_upper:  missing.append("uppercase letters")
        if not has_lower:  missing.append("lowercase letters")
        if not has_digit:  missing.append("numbers")
        if not has_symbol: missing.append("symbols")
        issues.append(f"missing: {', '.join(missing)}")

    # Repeated characters (aaa, 1111)
    if re.search(r"(.)\1{2,}", password):
        issues.append("contains repeated characters (e.g. 'aaa')")

    # Sequential characters (abcd, 1234)
    sequences = ["0123456789", "abcdefghijklmnopqrstuvwxyz", "qwertyuiop"]
    for seq in sequences:
        for i in range(len(seq) - 3):
            if seq[i:i+4] in pw_lower:
                issues.append(f"contains a sequential pattern ('{seq[i:i+4]}')")
                break

    # Common words as building blocks
    for word in COMMON_WORDS:
        if word in pw_lower:
            issues.append(f"contains common word '{word}'")
            break

    entropy = _estimate_entropy_bits(password)

    # Rating
    if entropy < 28 or len(issues) >= 3:
        rating, emoji = "VERY WEAK", "🔴"
    elif entropy < 36 or len(issues) >= 2:
        rating, emoji = "WEAK", "🟠"
    elif entropy < 60 or len(issues) >= 1:
        rating, emoji = "MODERATE", "🟡"
    elif entropy < 80:
        rating, emoji = "STRONG", "🟢"
    else:
        rating, emoji = "VERY STRONG", "🟢"

    log_info(f"[PasswordTool] Strength check: {rating} (~{entropy:.0f} bits)")

    result = f"{emoji} {rating} (~{entropy:.0f} bits of entropy)"

    if issues:
        result += "\nIssues: " + "; ".join(issues)
    else:
        result += "\nNo obvious weaknesses found."

    result += ("\n\nTip: say 'check password' separately to see if this "
                "password has appeared in any known data breaches.")

    return result


def check_password_strength_voice() -> str:
    """
    Voice-guided strength check — prompts for hidden input via terminal,
    same pattern as threat_intelligence.check_password_voice().
    """
    from core.voice_engine import speak
    speak("For privacy, please type the password in the terminal and press Enter Boss.")

    try:
        import getpass
        password = getpass.getpass("Type password (hidden): ")
    except Exception:
        password = input("Type password: ")

    return check_password_strength(password)