"""
check_voices.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One-time diagnostic script — run this on the Windows machine to
list ALL installed SAPI5 voices (name, id, language).

Run:
    python check_voices.py

This tells us whether a Hindi male voice (commonly "Microsoft Hemant"
on Windows 10/11, or "Microsoft Kalpana"/"Hemant" depending on language
pack) is already installed. If "Hemant" (male) is present, we can
configure voice_engine.py to use it for Hindi text — offline, fast,
and male — instead of gTTS's female-only Hindi voice.

If no Hindi voice is listed, Windows Settings > Time & Language >
Language > add "Hindi" and install its speech pack, which adds
"Microsoft Hemant" (male) and "Microsoft Kalpana"/"Swara" (female).
"""

import pyttsx3

engine = pyttsx3.init()
voices = engine.getProperty('voices')

print(f"Found {len(voices)} installed voice(s):\n")

for v in voices:
    langs = getattr(v, "languages", [])
    print(f"Name : {v.name}")
    print(f"ID   : {v.id}")
    print(f"Lang : {langs}")
    print(f"Gender: {getattr(v, 'gender', 'unknown')}")
    print("-" * 50)