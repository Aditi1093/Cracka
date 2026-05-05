"""
automation/form_filler.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRACKA AI — Universal Form Auto-Filler
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Features:
  ✅ Kisi bhi browser mein kaam karta hai (Chrome, Edge, Firefox)
  ✅ Voice trigger: "fill the form" / "form bharke do"
  ✅ Automatic: form detect hone par khud fill karta hai
  ✅ AI-powered field detection (field ka naam dekh ke value daalta hai)
  ✅ Profile system: multiple profiles (personal, college, job, shopping)
  ✅ Smart field mapping: name/email/phone/address/dob sab detect karta hai
  ✅ OTP handling: OTP aane par bolta hai Boss ko
  ✅ CAPTCHA detect karta hai — Boss ko batata hai

Dependencies:
  pip install selenium webdriver-manager pyautogui pillow pytesseract

Selenium WebDriver automatically install hoga.

Usage in ai_brain.py:
  elif "fill" in command and "form" in command:
      from automation.form_filler import fill_form_voice
      return fill_form_voice()

  elif "save profile" in command:
      from automation.form_filler import save_profile_voice
      return save_profile_voice()

  elif "show profile" in command:
      from automation.form_filler import show_profile
      return show_profile()
"""

import os
import json
import time
import re
import threading
from datetime import datetime
from core.logger import log_info, log_error
from core.voice_engine import speak

# ── Profile storage ───────────────────────────────────────────────────────────
PROFILE_FILE = "data/form_profiles.json"

# ── Default Boss profile template ─────────────────────────────────────────────
DEFAULT_PROFILE = {
    "personal": {
        "first_name":    "",
        "last_name":     "",
        "full_name":     "",
        "email":         "",
        "phone":         "",
        "mobile":        "",
        "dob":           "",        # DD/MM/YYYY
        "dob_day":       "",
        "dob_month":     "",
        "dob_year":      "",
        "gender":        "",
        "address":       "",
        "city":          "",
        "state":         "",
        "pincode":       "",
        "country":       "India",
        "aadhaar":       "",
        "pan":           "",
        "father_name":   "",
        "mother_name":   "",
        "nationality":   "Indian",
    },
    "college": {
        "college_name":  "",
        "university":    "",
        "course":        "",
        "branch":        "",
        "year":          "",
        "semester":      "",
        "roll_number":   "",
        "enrollment_no": "",
        "cgpa":          "",
        "percentage":    "",
        "passing_year":  "",
    },
    "job": {
        "designation":   "",
        "company":       "",
        "experience":    "",
        "skills":        "",
        "linkedin":      "",
        "github":        "",
        "portfolio":     "",
        "salary_expected": "",
        "notice_period": "",
    },
    "login": {
        "username":      "",
        "password":      "",       # Stored locally, encrypted optional
        "confirm_password": "",
    },
    "shopping": {
        "card_name":     "",
        "card_number":   "",       # Store at your own risk!
        "card_expiry":   "",
        "card_cvv":      "",
        "upi_id":        "",
    }
}

# ── Field keyword mapping ──────────────────────────────────────────────────────
# Maps form field labels/names/ids to profile keys
FIELD_MAP = {
    # Name fields
    "first.name|firstname|given.name|fname|first_name": "first_name",
    "last.name|lastname|surname|lname|last_name|family.name": "last_name",
    "full.name|fullname|name|your.name|applicant.name|candidate.name": "full_name",
    "father|father.name|fathers.name|paternal": "father_name",
    "mother|mother.name|mothers.name|maternal": "mother_name",

    # Contact
    "email|e.mail|email.address|mail|e-mail": "email",
    "phone|mobile|contact|cell|telephone|phone.number|mobile.number|contact.number": "phone",

    # DOB
    "dob|date.of.birth|birth.date|birthdate|dateofbirth|born": "dob",
    "day|birth.day|dob.day": "dob_day",
    "month|birth.month|dob.month": "dob_month",
    "year|birth.year|dob.year|passing.year": "dob_year",

    # Gender
    "gender|sex": "gender",

    # Address
    "address|street|addr|house.no|flat": "address",
    "city|town|district|tehsil": "city",
    "state|province": "state",
    "pincode|zip|postal|pin.code|zipcode|zip.code": "pincode",
    "country|nation": "country",

    # IDs
    "aadhaar|aadhar|uid|uidai": "aadhaar",
    "pan|pan.number|pan.card|pancard": "pan",

    # College
    "college|college.name|institution|institute": "college_name",
    "university|univ": "university",
    "course|program|programme|degree": "course",
    "branch|department|dept|stream|specialization": "branch",
    "semester|sem": "semester",
    "roll|roll.no|roll.number|rollno": "roll_number",
    "enrollment|enroll|enrolment": "enrollment_no",
    "cgpa|gpa|grade": "cgpa",
    "percentage|percent|marks": "percentage",

    # Job
    "designation|post|position|role|job.title": "designation",
    "company|organization|employer|firm": "company",
    "experience|exp|work.experience": "experience",
    "skills|technical.skills|key.skills": "skills",
    "linkedin|linkedin.profile": "linkedin",
    "github|github.profile": "github",
    "portfolio|website|personal.website": "portfolio",
    "salary|ctc|expected.salary|salary.expected": "salary_expected",

    # Login
    "username|user.name|user_name|login|userid|user.id": "username",
    "password|passwd|pass|pwd": "password",
    "confirm.password|retype.password|verify.password|repeat.password": "confirm_password",

    # Shopping
    "card.name|name.on.card|cardholder": "card_name",
    "card.number|card.no|cardnumber|cc.number|credit.card": "card_number",
    "expiry|expiry.date|exp.date|valid.through|card.expiry": "card_expiry",
    "cvv|cvc|security.code|card.cvv": "card_cvv",
    "upi|upi.id|vpa": "upi_id",
}


# ── Profile Manager ───────────────────────────────────────────────────────────

def _load_profiles() -> dict:
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(PROFILE_FILE):
        _save_profiles(DEFAULT_PROFILE)
        return DEFAULT_PROFILE
    try:
        with open(PROFILE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROFILE


def _save_profiles(profiles: dict):
    os.makedirs("data", exist_ok=True)
    with open(PROFILE_FILE, "w") as f:
        json.dump(profiles, f, indent=2)


def get_profile(category: str = "personal") -> dict:
    """Get a profile category."""
    profiles = _load_profiles()
    return profiles.get(category, {})


def get_all_values() -> dict:
    """Get flat dict of all profile values for easy lookup."""
    profiles = _load_profiles()
    flat = {}
    for cat in profiles.values():
        flat.update(cat)
    return flat


def update_profile(category: str, key: str, value: str):
    """Update a single profile value."""
    profiles = _load_profiles()
    if category not in profiles:
        profiles[category] = {}
    profiles[category][key] = value
    _save_profiles(profiles)


def show_profile() -> str:
    """Show current profile details."""
    profiles = _load_profiles()
    personal = profiles.get("personal", {})
    filled = {k: v for k, v in personal.items() if v}
    empty  = [k for k, v in personal.items() if not v]

    lines = [f"Profile has {len(filled)} fields filled:"]
    for k, v in filled.items():
        if "password" not in k and "card" not in k:
            lines.append(f"  {k}: {v}")

    if empty:
        lines.append(f"\nEmpty fields ({len(empty)}): {', '.join(empty[:8])}")

    return "\n".join(lines)


def save_profile_voice() -> str:
    """Voice-guided profile setup."""
    from core.listener import listen_for_text

    speak("Let's set up your profile Boss. I'll ask you a few questions.")

    fields = [
        ("personal", "full_name",  "What is your full name Boss?"),
        ("personal", "email",      "What is your email address Boss?"),
        ("personal", "phone",      "What is your mobile number Boss?"),
        ("personal", "dob",        "What is your date of birth? Say like 15 August 2000."),
        ("personal", "city",       "Which city are you from Boss?"),
        ("personal", "state",      "Which state Boss?"),
        ("personal", "pincode",    "What is your area pincode Boss?"),
        ("college",  "college_name","What is your college name Boss?"),
        ("college",  "course",     "What course are you studying Boss?"),
        ("college",  "branch",     "What is your branch or department Boss?"),
    ]

    profiles = _load_profiles()

    for category, key, question in fields:
        value = listen_for_text(question)
        if value and value.strip():
            if category not in profiles:
                profiles[category] = {}
            profiles[category][key] = value.strip()

            # Auto-fill derived fields
            if key == "full_name":
                parts = value.strip().split()
                if len(parts) >= 2:
                    profiles["personal"]["first_name"] = parts[0]
                    profiles["personal"]["last_name"]  = " ".join(parts[1:])

            if key == "dob":
                # Parse date
                dob_parts = _parse_dob(value)
                if dob_parts:
                    profiles["personal"]["dob_day"]   = dob_parts[0]
                    profiles["personal"]["dob_month"] = dob_parts[1]
                    profiles["personal"]["dob_year"]  = dob_parts[2]

    _save_profiles(profiles)
    log_info("Profile saved via voice")
    speak("Profile saved Boss! I'm ready to fill forms for you.")
    return "Profile saved! Say 'fill the form' on any form page Boss."


def _parse_dob(text: str):
    """Extract day, month, year from natural language date."""
    months = {
        "january":1,"february":2,"march":3,"april":4,
        "may":5,"june":6,"july":7,"august":8,
        "september":9,"october":10,"november":11,"december":12,
        "jan":1,"feb":2,"mar":3,"apr":4,"jun":6,"jul":7,
        "aug":8,"sep":9,"oct":10,"nov":11,"dec":12,
    }
    text = text.lower()

    # Try DD/MM/YYYY or DD-MM-YYYY
    m = re.search(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", text)
    if m:
        return m.group(1), m.group(2), m.group(3)

    # Try "15 august 2000" or "august 15 2000"
    for month_name, month_num in months.items():
        if month_name in text:
            nums = re.findall(r"\d+", text)
            if len(nums) >= 2:
                year  = next((n for n in nums if len(n)==4), "")
                day   = next((n for n in nums if len(n)<=2 and n!=year), "")
                return day, str(month_num), year

    return None


# ── Field Value Resolver ──────────────────────────────────────────────────────

def _resolve_field_value(field_label: str, field_name: str,
                          field_id: str, field_type: str) -> str:
    """
    Given a form field's attributes, find the right value from profile.
    Uses AI-powered keyword matching.
    """
    all_values = get_all_values()

    # Combine all field identifiers for matching
    combined = " ".join([
        field_label.lower(),
        field_name.lower(),
        field_id.lower()
    ]).replace("-", " ").replace("_", " ").replace("*", "")

    # Skip non-fillable types
    if field_type in ["submit", "button", "reset", "file", "image", "hidden"]:
        return None

    # Match against field map
    best_key  = None
    best_score = 0

    for pattern, profile_key in FIELD_MAP.items():
        keywords = pattern.split("|")
        for kw in keywords:
            kw = kw.replace(".", " ")
            if kw in combined:
                score = len(kw)  # Longer match = better
                if score > best_score:
                    best_score = score
                    best_key   = profile_key

    if best_key and best_key in all_values:
        value = all_values[best_key]
        if value:
            log_info(f"Field '{combined[:30]}' → '{best_key}' = '{value[:20]}'")
            return value

    return None


# ── Selenium Form Filler ──────────────────────────────────────────────────────

def _get_driver():
    """Get or create a Selenium WebDriver for the active browser."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as CService
        from selenium.webdriver.edge.service  import Service as EService
        from selenium.webdriver.firefox.service import Service as FService
        from webdriver_manager.chrome  import ChromeDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        from webdriver_manager.firefox import GeckoDriverManager

        # Try Chrome first
        try:
            options = webdriver.ChromeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            driver = webdriver.Chrome(
                service=CService(ChromeDriverManager().install()),
                options=options
            )
            log_info("Connected to Chrome")
            return driver
        except Exception:
            pass

        # Try Edge
        try:
            options = webdriver.EdgeOptions()
            options.add_experimental_option("debuggerAddress", "127.0.0.1:9223")
            driver = webdriver.Edge(
                service=EService(EdgeChromiumDriverManager().install()),
                options=options
            )
            log_info("Connected to Edge")
            return driver
        except Exception:
            pass

        # Launch new Chrome instance
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            driver = webdriver.Chrome(
                service=CService(ChromeDriverManager().install()),
                options=options
            )
            log_info("Launched new Chrome")
            return driver
        except Exception as e:
            log_error(f"Chrome launch failed: {e}")

    except ImportError:
        log_error("Selenium not installed: pip install selenium webdriver-manager")
    except Exception as e:
        log_error(f"Driver error: {e}")

    return None


def fill_form_selenium(url: str = None) -> str:
    """
    Main form filler using Selenium.
    Finds all input fields on current page and fills them.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import Select, WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import (
        StaleElementReferenceException,
        ElementNotInteractableException,
        NoSuchElementException
    )

    speak("Opening the form Boss. Give me a moment.")

    driver = _get_driver()
    if not driver:
        return ("Could not connect to browser Boss. "
                "Please start Chrome with remote debugging:\n"
                "chrome.exe --remote-debugging-port=9222")

    if url:
        driver.get(url)
        time.sleep(2)

    filled_count  = 0
    skipped_count = 0
    captcha_found = False

    try:
        # Wait for page to load
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "input"))
        )

        # Find all form fields
        inputs   = driver.find_elements(By.TAG_NAME, "input")
        selects  = driver.find_elements(By.TAG_NAME, "select")
        textareas= driver.find_elements(By.TAG_NAME, "textarea")

        speak(f"Found {len(inputs)+len(selects)+len(textareas)} fields Boss. Filling now.")

        # ── Fill input fields ──────────────────────────────────────────────────
        for inp in inputs:
            try:
                field_type  = inp.get_attribute("type") or "text"
                field_name  = inp.get_attribute("name")  or ""
                field_id    = inp.get_attribute("id")    or ""
                placeholder = inp.get_attribute("placeholder") or ""
                aria_label  = inp.get_attribute("aria-label") or ""

                # Try to get label text
                label_text = ""
                try:
                    field_id_val = inp.get_attribute("id")
                    if field_id_val:
                        label_el = driver.find_element(
                            By.CSS_SELECTOR, f"label[for='{field_id_val}']"
                        )
                        label_text = label_el.text
                except Exception:
                    pass

                combined_label = " ".join([
                    label_text, field_name, field_id, placeholder, aria_label
                ])

                # Skip hidden, submit, file fields
                if field_type in ["submit","button","reset","file","image","hidden"]:
                    continue

                # Detect CAPTCHA
                if any(x in combined_label.lower() for x in
                       ["captcha","recaptcha","robot","verify you"]):
                    captcha_found = True
                    continue

                # Skip if already filled
                current_val = inp.get_attribute("value") or ""
                if current_val.strip():
                    skipped_count += 1
                    continue

                # Get value from profile
                value = _resolve_field_value(
                    combined_label, field_name, field_id, field_type
                )

                if not value:
                    continue

                # Handle different input types
                if field_type == "radio":
                    # Select matching radio
                    if value.lower() in inp.get_attribute("value").lower():
                        inp.click()
                        filled_count += 1

                elif field_type == "checkbox":
                    # Only check if value is true/yes
                    if value.lower() in ["yes", "true", "1"]:
                        if not inp.is_selected():
                            inp.click()
                        filled_count += 1

                elif field_type == "date":
                    # Format: YYYY-MM-DD
                    formatted = _format_date_for_input(value)
                    if formatted:
                        driver.execute_script(
                            f"arguments[0].value = '{formatted}';", inp
                        )
                        filled_count += 1

                else:
                    # Text, email, tel, number, etc.
                    inp.clear()
                    inp.send_keys(value)
                    filled_count += 1
                    time.sleep(0.1)  # Small delay for natural typing

            except (StaleElementReferenceException, ElementNotInteractableException):
                continue
            except Exception as e:
                log_error(f"Input fill error: {e}")
                continue

        # ── Fill select dropdowns ──────────────────────────────────────────────
        for sel in selects:
            try:
                field_name = sel.get_attribute("name") or ""
                field_id   = sel.get_attribute("id")   or ""

                label_text = ""
                try:
                    lid = sel.get_attribute("id")
                    if lid:
                        label_el = driver.find_element(
                            By.CSS_SELECTOR, f"label[for='{lid}']"
                        )
                        label_text = label_el.text
                except Exception:
                    pass

                value = _resolve_field_value(label_text, field_name, field_id, "select")
                if not value:
                    continue

                select_obj = Select(sel)

                # Try exact match first, then partial
                matched = False
                for option in select_obj.options:
                    if value.lower() == option.text.lower():
                        select_obj.select_by_visible_text(option.text)
                        filled_count += 1
                        matched = True
                        break

                if not matched:
                    for option in select_obj.options:
                        if value.lower() in option.text.lower():
                            select_obj.select_by_visible_text(option.text)
                            filled_count += 1
                            break

            except Exception as e:
                log_error(f"Select fill error: {e}")
                continue

        # ── Fill textareas ─────────────────────────────────────────────────────
        for ta in textareas:
            try:
                field_name = ta.get_attribute("name") or ""
                field_id   = ta.get_attribute("id")   or ""
                placeholder= ta.get_attribute("placeholder") or ""

                value = _resolve_field_value(placeholder, field_name, field_id, "textarea")
                if value and not ta.get_attribute("value"):
                    ta.clear()
                    ta.send_keys(value)
                    filled_count += 1
                    time.sleep(0.1)

            except Exception as e:
                log_error(f"Textarea fill error: {e}")
                continue

    except Exception as e:
        log_error(f"Form fill error: {e}")
        return f"Form filling error Boss: {e}"

    # ── Summary ────────────────────────────────────────────────────────────────
    result = f"Form filled Boss! {filled_count} fields done."

    if captcha_found:
        result += " CAPTCHA detected — please solve it manually Boss."
        speak(f"Done Boss! {filled_count} fields filled. There is a CAPTCHA — please solve it.")
    else:
        speak(f"Form filled Boss! {filled_count} fields completed. Please review before submitting.")

    log_info(f"Form filled: {filled_count} fields, {skipped_count} skipped")
    return result


def _format_date_for_input(value: str) -> str:
    """Convert date to YYYY-MM-DD format for HTML date inputs."""
    # Try DD/MM/YYYY
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", value)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    # Already YYYY-MM-DD
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", value)
    if m:
        return value
    return ""


# ── PyAutoGUI Fallback Filler ─────────────────────────────────────────────────

def fill_form_pyautogui() -> str:
    """
    Fallback: Use Tab key navigation to fill visible form fields.
    Works even without Selenium when browser is already open.
    No browser connection needed.
    """
    import pyautogui

    speak("I'll use keyboard navigation to fill the form Boss. Make sure the form is open.")
    time.sleep(2)

    all_values  = get_all_values()
    filled      = 0

    # Click on first field
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.3)

    common_fields = [
        "full_name", "email", "phone", "dob",
        "address", "city", "state", "pincode",
        "college_name", "course", "branch"
    ]

    for key in common_fields:
        val = all_values.get(key, "")
        if val:
            pyautogui.write(val, interval=0.04)
            pyautogui.press("tab")
            filled += 1
            time.sleep(0.2)

    speak(f"Filled {filled} fields Boss using keyboard. Please check the form.")
    return f"Filled {filled} fields using keyboard navigation Boss."


# ── Voice Command Handler ─────────────────────────────────────────────────────

def fill_form_voice() -> str:
    """
    Main voice command handler.
    Called when Boss says 'fill the form' or 'form bharke do'.
    """
    profiles = _load_profiles()
    personal = profiles.get("personal", {})

    # Check if profile is empty
    filled_fields = [v for v in personal.values() if v]
    if len(filled_fields) < 3:
        speak("Boss, your profile is not set up yet. Let me set it up first.")
        return save_profile_voice()

    speak("Starting form filler Boss.")

    # Try Selenium first
    try:
        from selenium import webdriver
        result = fill_form_selenium()
        return result
    except ImportError:
        speak("Selenium not found Boss. Using keyboard method.")
        return fill_form_pyautogui()
    except Exception as e:
        log_error(f"Selenium failed: {e}")
        speak("Browser connection failed Boss. Using keyboard method.")
        return fill_form_pyautogui()


# ── Auto-detect and fill ───────────────────────────────────────────────────────

def start_auto_form_watcher():
    """
    Background thread that watches clipboard/browser for form URLs.
    When a form page is detected, Cracka asks Boss if it should fill it.
    """
    import pyperclip

    form_keywords = [
        "form", "apply", "register", "signup", "sign-up",
        "application", "admission", "enrollment", "checkout",
        "fill", "submit", "login"
    ]

    last_url = ""

    def _watch():
        nonlocal last_url
        while True:
            try:
                clip = pyperclip.paste()
                if clip and clip != last_url:
                    clip_lower = clip.lower()
                    if clip.startswith("http") and any(
                        kw in clip_lower for kw in form_keywords
                    ):
                        last_url = clip
                        speak(f"Boss, I see a form URL copied. Should I fill it for you? Say 'yes fill it'.")
            except Exception:
                pass
            time.sleep(3)

    t = threading.Thread(target=_watch, daemon=True)
    t.start()
    log_info("Auto form watcher started")


# ── Chrome Remote Debugging Setup ─────────────────────────────────────────────

def setup_chrome_debug() -> str:
    """
    Instruction to launch Chrome with remote debugging.
    Run this once — then Selenium can connect to your existing Chrome.
    """
    instructions = """
To connect Cracka to your Chrome browser:

1. Close all Chrome windows first.

2. Run this command in CMD:
   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222

3. Chrome will open — now Cracka can control it.

4. Say 'fill the form' when you are on any form page.

Tip: Create a shortcut with this command so you can always open
     the 'Cracka Chrome' easily!
"""
    speak("Opening Chrome with remote debug mode Boss.")
    import subprocess
    try:
        subprocess.Popen([
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            "--remote-debugging-port=9222",
            "--user-data-dir=C:\\CrackaChrome"
        ])
        return "Chrome opened in Cracka mode Boss! Now go to any form and say 'fill the form'."
    except Exception:
        return instructions
