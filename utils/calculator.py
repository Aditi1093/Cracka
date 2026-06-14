"""
╔══════════════════════════════════════════════════════════════╗
║         CRACKA AI — UNIVERSE CALCULATOR                      ║
║   utils/calculator.py                                        ║
║   Voice → math. Any number. Any operation. Instant answer.  ║
╚══════════════════════════════════════════════════════════════╝

SUPPORTS:
  Basic      : "calculate 25 times 4"
  Precision  : "0.1 plus 0.2"          → 0.3 (not 0.30000000000004)
  Big nums   : "2 to the power of 64"  → exact 20-digit answer
  Factorial  : "factorial of 100"       → exact 158-digit answer
  Roots      : "square root of 144", "cube root of 27"
  Logs       : "log of 1000", "natural log of 2.718"
  Trig       : "sine of 90 degrees", "cosine of 0"
  GCD / LCM  : "gcd of 48 and 18"
  Prime      : "is 97 prime", "prime factors of 60"
  Percentage : "15 percent of 200"
  Modulo     : "17 mod 5"
  Hinglish   : "25 aur 4 ka guna", "100 mein se 5 ghata"
  Constants  : "what is pi", "value of e"
"""

import re
import math
from decimal import Decimal, getcontext, InvalidOperation
from core.logger import log_error

# 50-digit precision — handles factorial(100), 2^200 etc.
getcontext().prec = 50

# ─── Word → symbol map  (ORDER CRITICAL: longest/most-specific FIRST) ────────
_REPLACEMENTS = [
    # multi-word phrases — MUST come before their sub-words
    ("square root of",   "__sqrt__"),
    ("cube root of",     "__cbrt__"),
    ("log base 10 of",   "__log10__"),
    ("log base 2 of",    "__log2__"),
    ("natural log of",   "__ln__"),
    ("log of",           "__log10__"),
    ("to the power of",  "**"),
    ("multiplied by",    "*"),
    ("divided by",       "/"),
    ("take away",        "-"),
    ("percent of",       "*0.01*"),
    # Hinglish — "ka guna" BEFORE "ka" (else "ka" eats it first)
    ("ka guna",          "*"),
    ("mein se",          "-"),     # "100 mein se 5" = 100-5
    # single-word operators
    ("plus",             "+"),
    ("minus",            "-"),
    ("times",            "*"),
    ("over",             "/"),
    ("divide",           "/"),
    ("multiply",         "*"),
    ("add",              "+"),
    ("subtract",         "-"),
    ("power",            "**"),
    ("squared",          "**2"),
    ("cubed",            "**3"),
    ("mod",              "%"),
    ("modulo",           "%"),
    ("remainder",        "%"),
    # constants
    ("pi",               str(math.pi)),
    ("euler",            str(math.e)),
    # Hinglish single words
    ("aur",              "+"),
    ("ghata",            "-"),
    ("guna",             "*"),
    ("bhaag",            "/"),
    # cleanup connector — LAST
    ("ka",               ""),
]

_STRIP_WORDS = [
    "calculate", "calculation", "calculator", "math", "maths",
    "what is", "what's", "compute", "solve", "equals", "equal to",
    "find", "tell me", "boss", "cracka", "the answer to",
    "hisab", "hisab karo", "kitna hai", "kitna hoga", "bolo", "batao",
]


# ─── Public API ───────────────────────────────────────────────────────────────

def calculate(command: str) -> str:
    """Main entry. Called from ai_brain.py."""
    cmd = command.lower().strip()

    # Step 1: special commands (factorial, trig, prime, gcd …)
    special = _try_special(cmd)
    if special is not None:
        return special

    # Step 2: Hinglish compound patterns (BEFORE word replacement)
    cmd = _hinglish_preprocess(cmd)

    # Step 3: normal expression pipeline
    expr = _strip_triggers(cmd)
    expr = _replace_words(expr)
    expr = _replace_placeholders(expr)
    expr = re.sub(r"\s+", "", expr)
    # clean trailing dangling operator left by Hinglish patterns
    expr = re.sub(r"[+\-*/%]+$", "", expr).strip()

    if not expr:
        return "Please say a math problem Boss. Like 'calculate 25 times 4'."

    return _safe_eval(expr, command)


# ─── Special handlers ─────────────────────────────────────────────────────────

def _try_special(cmd: str):
    """Returns string if special pattern matched, else None."""

    # Factorial
    m = (re.search(r"factorial\s+(?:of\s+)?(\d+)", cmd) or
         re.search(r"(\d+)\s*factorial", cmd))
    if m:
        n = int(m.group(1))
        if n > 10_000:
            return f"That factorial is too large Boss ({n}!). Try under 10,000."
        r = math.factorial(n)
        s = str(r)
        if len(s) > 40:
            sci = f"{Decimal(s):.6E}"
            return f"Factorial of {n} is {sci} Boss. (Exact answer has {len(s)} digits.)"
        return f"Factorial of {n} is {r:,} Boss."

    # GCD
    m = re.search(r"gcd\s+(?:of\s+)?(\d+)\s+and\s+(\d+)", cmd)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return f"GCD of {a} and {b} is {math.gcd(a, b)} Boss."

    # LCM
    m = re.search(r"lcm\s+(?:of\s+)?(\d+)\s+and\s+(\d+)", cmd)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        lcm = abs(a * b) // math.gcd(a, b)
        return f"LCM of {a} and {b} is {lcm:,} Boss."

    # Prime check
    m = re.search(r"(?:is\s+)?(\d+)\s+(?:a\s+)?prime", cmd)
    if m:
        n = int(m.group(1))
        return f"{n} {'is' if _is_prime(n) else 'is not'} a prime number Boss."

    # Prime factors
    m = re.search(r"prime\s+factors?\s+(?:of\s+)?(\d+)", cmd)
    if m:
        n = int(m.group(1))
        return f"Prime factors of {n} are: {', '.join(map(str, _prime_factors(n)))} Boss."

    # Trig (always degrees — voice friendly)
    # NOTE: \bsin\b so "cosine" does NOT match sin pattern
    m = re.search(r"\bsin(?:e)?\s+(?:of\s+)?(-?[\d.]+)", cmd)
    if m:
        return f"Sine of {m.group(1)} degrees is {_trig(math.sin, float(m.group(1)))} Boss."

    m = re.search(r"cos(?:ine)?\s+(?:of\s+)?(-?[\d.]+)", cmd)
    if m:
        return f"Cosine of {m.group(1)} degrees is {_trig(math.cos, float(m.group(1)))} Boss."

    m = re.search(r"tan(?:gent)?\s+(?:of\s+)?(-?[\d.]+)", cmd)
    if m:
        deg = float(m.group(1))
        if deg % 180 == 90:
            return "Tangent of 90 degrees is undefined Boss (infinity)."
        return f"Tangent of {deg} degrees is {_trig(math.tan, deg)} Boss."

    # Percentage: "15 percent of 200"
    m = re.search(r"(-?[\d.]+)\s+percent(?:age)?\s+(?:of\s+)?(-?[\d.]+)", cmd)
    if m:
        pct, total = float(m.group(1)), float(m.group(2))
        result = pct * total / 100
        return f"{pct}% of {total} is {_fmt(result)} Boss."

    # Modulo (catch before normal pipeline since "mod" can confuse)
    m = re.search(r"(\d+)\s+mod(?:ulo)?\s+(\d+)", cmd)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if b == 0:
            return "Cannot mod by zero Boss."
        return f"{a} mod {b} is {a % b} Boss."

    # log(e) = 1 exactly
    if re.search(r"(?:natural\s+log|ln)\s+(?:of\s+)?e\b", cmd):
        return "Natural log of e is 1 Boss."

    # Constants
    if re.search(r"(?:value\s+of\s+|what\s+is\s+)pi\b", cmd):
        return f"Pi is {math.pi} Boss."
    if re.search(r"(?:value\s+of\s+|what\s+is\s+)e\b", cmd):
        return f"Euler's number e is {math.e} Boss."

    return None


# ─── Expression pipeline ──────────────────────────────────────────────────────

def _hinglish_preprocess(cmd: str) -> str:
    """Regex-based Hinglish compound patterns — run BEFORE word replacement."""
    # "25 aur 4 ka guna"  → "25*4"  (multiply)
    cmd = re.sub(r"(\d+\.?\d*)\s+aur\s+(\d+\.?\d*)\s+ka\s+guna",  r"\1*\2",  cmd)
    # "100 aur 5 ka bhaag" → "100/5" (divide)
    cmd = re.sub(r"(\d+\.?\d*)\s+aur\s+(\d+\.?\d*)\s+ka\s+bhaag", r"\1/\2",  cmd)
    # "5 aur 3 ka jod"     → "5+3"   (add)
    cmd = re.sub(r"(\d+\.?\d*)\s+aur\s+(\d+\.?\d*)\s+ka\s+jod",   r"\1+\2",  cmd)
    # "100 mein se 5"      → "100-5" (subtract)
    cmd = re.sub(r"(\d+\.?\d*)\s+mein\s+se\s+(\d+\.?\d*)",         r"\1-\2",  cmd)
    return cmd


def _strip_triggers(cmd: str) -> str:
    for w in sorted(_STRIP_WORDS, key=len, reverse=True):
        cmd = cmd.replace(w, " ")
    return cmd.strip()


def _replace_words(expr: str) -> str:
    for word, symbol in _REPLACEMENTS:
        expr = expr.replace(word, symbol)
    return expr


def _replace_placeholders(expr: str) -> str:
    expr = re.sub(r"__sqrt__\s*(-?[\d.]+)",  r"math.sqrt(\1)",     expr)
    expr = re.sub(r"__cbrt__\s*(-?[\d.]+)",  r"math.pow(\1,1/3)",  expr)
    expr = re.sub(r"__log10__\s*(-?[\d.]+)", r"math.log10(\1)",    expr)
    expr = re.sub(r"__log2__\s*(-?[\d.]+)",  r"math.log2(\1)",     expr)
    expr = re.sub(r"__ln__\s*(-?[\d.]+)",    r"math.log(\1)",      expr)
    # fallback for "(expr)" form
    expr = re.sub(r"__sqrt__\(",  "math.sqrt(",  expr)
    expr = re.sub(r"__cbrt__\(",  "math.pow(",   expr)
    expr = re.sub(r"__log10__\(", "math.log10(", expr)
    expr = re.sub(r"__log2__\(",  "math.log2(",  expr)
    expr = re.sub(r"__ln__\(",    "math.log(",   expr)
    return expr


# ─── Safe evaluator ───────────────────────────────────────────────────────────

def _safe_eval(expr: str, original: str) -> str:
    SG = {"__builtins__": {}}
    SL = {
        "math": math, "Decimal": Decimal,
        "sqrt": math.sqrt, "log": math.log,
        "log2": math.log2, "log10": math.log10,
        "abs": abs, "round": round, "pow": pow,
        "pi": math.pi, "e": math.e,
    }
    try:
        # Decimal path — pure arithmetic (no math. calls)
        if "math." not in expr:
            de = re.sub(
                r"(?<![a-zA-Z_'\"])(\d+\.?\d*)",
                lambda m: f"Decimal('{m.group(1)}')",
                expr
            )
            result = eval(de, SG, SL)
        else:
            result = eval(expr, SG, SL)
        return _format_result(result)

    except ZeroDivisionError:
        return "Cannot divide by zero Boss."
    except OverflowError:
        return "That number is too large even for me Boss."
    except (ValueError, InvalidOperation) as e:
        log_error(f"Calc ValueError: {e} | expr: {expr}")
        return "Invalid math operation Boss. Check your numbers."
    except SyntaxError:
        log_error(f"Calc SyntaxError | expr: {expr}")
        return "Could not understand that Boss. Try: 'calculate 25 times 4'."
    except Exception as e:
        log_error(f"Calc error: {e} | expr: {expr} | original: {original}")
        return "Could not calculate that Boss. Try saying it differently."


# ─── Formatters ───────────────────────────────────────────────────────────────

def _format_result(result) -> str:
    if isinstance(result, Decimal):
        s = str(result.normalize())
        if "E" in s:
            try:
                return f"The answer is {int(result):,} Boss."
            except Exception:
                pass
        return f"The answer is {s} Boss."

    if isinstance(result, float):
        if math.isnan(result):  return "That gives an undefined result Boss."
        if math.isinf(result):  return "That result is infinite Boss."
        if abs(result - round(result)) < 1e-10 and abs(result) < 1e15:
            return f"The answer is {int(round(result)):,} Boss."
        return f"The answer is {result:.10g} Boss."

    if isinstance(result, int):
        if abs(result) > 1_000_000_000_000:
            sci = f"{result:.6E}"
            return f"The answer is {sci} Boss. ({len(str(abs(result)))} digits)"
        return f"The answer is {result:,} Boss."

    return f"The answer is {result} Boss."


def _fmt(val: float) -> str:
    if abs(val - round(val)) < 1e-10:
        return str(int(round(val)))
    return f"{val:.8g}"


def _trig(fn, deg: float) -> str:
    v = fn(math.radians(deg))
    return _fmt(v)


# ─── Math utilities ───────────────────────────────────────────────────────────

def _is_prime(n: int) -> bool:
    if n < 2:   return False
    if n == 2:  return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True


def _prime_factors(n: int) -> list:
    factors, d = [], 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors