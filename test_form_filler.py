"""
test_form_filler.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
Form Filler ka quick test — NO browser, NO Selenium needed!

Tests:
  1. Profile save/load karna
  2. Date format conversion (main bug fix)
  3. Field keyword matching
  4. show_profile()

Run from project ROOT:
  python test_form_filler.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from automation.form_filler import (
    _load_profiles, _save_profiles, _parse_dob,
    _format_date_for_input, _resolve_field_value,
    show_profile, get_all_values, DEFAULT_PROFILE
)


def section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def check(label, result, expected=None):
    if expected is not None:
        ok = result == expected
        status = "✅" if ok else "❌"
        print(f"  {status} {label}")
        print(f"       Got      : {repr(result)}")
        if not ok:
            print(f"       Expected : {repr(expected)}")
    else:
        ok = bool(result)
        status = "✅" if ok else "❌"
        print(f"  {status} {label}: {result}")
    return ok


# ─────────────────────────────────────────────────────────────────────────────
# 1. SETUP — write a fake profile
# ─────────────────────────────────────────────────────────────────────────────
section("1. Setup — save a test profile")

test_profile = {
    "personal": {
        "first_name": "Aditi",
        "last_name":  "Patil",
        "full_name":  "Aditi Patil",
        "email":      "aditi@example.com",
        "phone":      "9999999999",
        "mobile":     "9999999999",
        "dob":        "15 August 2000",   # natural language — the bug case!
        "dob_day":    "15",
        "dob_month":  "8",
        "dob_year":   "2000",
        "gender":     "Female",
        "city":       "Rajura",
        "state":      "Maharashtra",
        "pincode":    "442905",
        "country":    "India",
        "nationality":"Indian",
        "aadhaar": "", "pan": "", "address": "",
        "father_name": "", "mother_name": "",
    },
    "college": {
        "college_name":  "Government Polytechnic Chandrapur",
        "course":        "Computer Engineering",
        "branch":        "Computer Science",
        "year":          "3",
        "semester":      "6",
        "roll_number":   "2201234",
        "enrollment_no": "EN2022CS001",
        "cgpa":          "8.5",
        "percentage":    "85",
        "university":    "",
        "passing_year":  "2025",
    },
    "job": {
        "designation": "AI Developer",
        "skills":      "Python, AI, Cybersecurity",
        "github":      "https://github.com/Aditi1093",
        "company": "", "experience": "", "linkedin": "",
        "portfolio": "", "salary_expected": "", "notice_period": "",
    },
    "login": {"username": "", "password": "", "confirm_password": ""},
    "shopping": {"card_name": "", "card_number": "", "card_expiry": "",
                 "card_cvv": "", "upi_id": ""},
}

_save_profiles(test_profile)
loaded = _load_profiles()
check("Profile saved and loaded", loaded.get("personal", {}).get("full_name"), "Aditi Patil")
print(f"  ℹ️  Profile file: data/form_profiles.json")


# ─────────────────────────────────────────────────────────────────────────────
# 2. DATE PARSING — _parse_dob()
# ─────────────────────────────────────────────────────────────────────────────
section("2. Date Parsing — _parse_dob()")

cases_parse = [
    ("15 august 2000",    ("15", "8", "2000")),
    ("august 15 2000",    ("15", "8", "2000")),
    ("15/08/2000",        ("15", "08", "2000")),
    ("15-08-2000",        ("15", "08", "2000")),
    ("1 january 1999",    ("1",  "1", "1999")),
    ("march 22 2001",     ("22", "3", "2001")),
]

all_ok = True
for text, expected in cases_parse:
    result = _parse_dob(text)
    ok = check(f'_parse_dob("{text}")', result, expected)
    all_ok = all_ok and ok


# ─────────────────────────────────────────────────────────────────────────────
# 3. DATE FORMAT — _format_date_for_input()  ← THE MAIN BUG FIX
# ─────────────────────────────────────────────────────────────────────────────
section("3. Date Format for HTML input — _format_date_for_input()")
print("  (HTML <input type='date'> needs YYYY-MM-DD with zero-padding)")

cases_fmt = [
    # Natural language — this was the bug (returned "" before fix)
    ("15 august 2000",   "2000-08-15"),
    ("1 january 1999",   "1999-01-01"),
    ("march 22 2001",    "2001-03-22"),
    # DD/MM/YYYY
    ("15/08/2000",       "2000-08-15"),
    ("1/1/1999",         "1999-01-01"),
    # Already YYYY-MM-DD (zero-padding was missing before fix)
    ("2000-8-5",         "2000-08-05"),   # was returning "2000-8-5" before!
    ("2000-08-15",       "2000-08-15"),   # already correct
]

for text, expected in cases_fmt:
    check(f'_format_date_for_input("{text}")', _format_date_for_input(text), expected)


# ─────────────────────────────────────────────────────────────────────────────
# 4. FIELD KEYWORD MATCHING — _resolve_field_value()
# ─────────────────────────────────────────────────────────────────────────────
section("4. Field Keyword Matching")
print("  (Simulates what happens when Cracka sees a form field)")

cases_field = [
    # (label, name, id, type) → expected profile value
    ("Full Name",       "fullname",      "fullName",    "text",  "Aditi Patil"),
    ("Email Address",   "email",         "email",       "email", "aditi@example.com"),
    ("Mobile Number",   "mobile",        "phone",       "tel",   "9999999999"),
    ("Date of Birth",   "dob",           "dateOfBirth", "date",  "15 August 2000"),
    ("City",            "city",          "city",        "text",  "Rajura"),
    ("State",           "state",         "state",       "text",  "Maharashtra"),
    ("Pincode",         "pincode",       "zipCode",     "text",  "442905"),
    ("College Name",    "collegeName",   "college",     "text",  "Government Polytechnic Chandrapur"),
    ("Branch",          "branch",        "dept",        "text",  "Computer Science"),
    ("Roll Number",     "rollNo",        "roll",        "text",  "2201234"),
    ("GitHub Profile",  "github",        "github",      "url",   "https://github.com/Aditi1093"),
]

for label, name, field_id, ftype, expected in cases_field:
    result = _resolve_field_value(label, name, field_id, ftype)
    check(f'Field "{label}"', result, expected)


# ─────────────────────────────────────────────────────────────────────────────
# 5. SHOW PROFILE
# ─────────────────────────────────────────────────────────────────────────────
section("5. show_profile() — what Boss sees when asking 'show profile'")
print(show_profile())


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
section("✅ TEST COMPLETE")
print("""
If all checkboxes above are ✅, form filler is working correctly!

To use in Cracka (voice):
  1. Say: 'save profile' — set up your info via voice
  2. Go to any form in browser
  3. Say: 'open cracka chrome' — launches Chrome in debug mode
  4. Navigate to the form
  5. Say: 'fill the form' — Cracka fills it automatically!

Note: 'fill the form' needs Selenium:
  pip install selenium webdriver-manager
""")