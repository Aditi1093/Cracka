"""
list_edge_voices.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One-time diagnostic — run this to list ALL available edge-tts voices
and verify which ones in voice_engine.py's EDGE_VOICE_MAP actually
exist on your edge-tts version (voice availability can change).

Run:
    python list_edge_voices.py

If a mapped voice shows as "NOT FOUND", edge-tts will throw an
error for that language, causing voice_engine.py to silently fall
back to the English pyttsx3 voice (David) — which is likely why
"different voice each time" was observed: some languages' voices
don't exist, so they fell back to English/David while others (with
valid voices) used the correct male Neural voice.
"""

import asyncio
import edge_tts

# Same map as in voice_engine.py — keep in sync
EDGE_VOICE_MAP = {
    "hi": "hi-IN-MadhurNeural", "mr": "mr-IN-ManoharNeural",
    "fr": "fr-FR-HenriNeural", "es": "es-ES-AlvaroNeural",
    "de": "de-DE-ConradNeural", "ja": "ja-JP-KeitaNeural",
    "zh-CN": "zh-CN-YunxiNeural", "ar": "ar-SA-HamedNeural",
    "pt": "pt-PT-DuarteNeural", "ru": "ru-RU-DmitryNeural",
    "it": "it-IT-DiegoNeural", "ko": "ko-KR-InJoonNeural",
    "gu": "gu-IN-NiranjanNeural", "ta": "ta-IN-ValluvarNeural",
    "te": "te-IN-MohanNeural", "bn": "bn-IN-BashkarNeural",
    "pa": "hi-IN-MadhurNeural", "ur": "ur-PK-AsadNeural",
    "ml": "ml-IN-MidhunNeural", "kn": "kn-IN-GaganNeural",
    "or": "or-IN-SukantNeural", "vi": "vi-VN-NamMinhNeural",
    "th": "th-TH-NiwatNeural", "tr": "tr-TR-AhmetNeural",
    "pl": "pl-PL-MarekNeural", "nl": "nl-NL-MaartenNeural",
    "el": "el-GR-NestorasNeural", "iw": "he-IL-AvriNeural",
    "id": "id-ID-ArdiNeural", "uk": "uk-UA-OstapNeural",
    "fa": "fa-IR-FaridNeural", "en": "en-US-GuyNeural",
}


async def main():
    voices = await edge_tts.list_voices()
    all_names = {v["ShortName"] for v in voices}

    print(f"Total available edge-tts voices: {len(all_names)}\n")
    print("Checking EDGE_VOICE_MAP entries:\n")

    missing = []
    for lang, voice_name in EDGE_VOICE_MAP.items():
        status = "OK" if voice_name in all_names else "NOT FOUND"
        print(f"  {lang:8s} -> {voice_name:25s} [{status}]")
        if status == "NOT FOUND":
            missing.append((lang, voice_name))

    if missing:
        print(f"\n{len(missing)} voice(s) NOT FOUND. Suggested replacements "
              f"(any male voice for that language):\n")
        for lang, voice_name in missing:
            prefix = voice_name.split("-")[0] + "-" + voice_name.split("-")[1]
            candidates = [v["ShortName"] for v in voices
                          if v["ShortName"].startswith(prefix)]
            print(f"  {lang:8s} (wanted {voice_name}): available -> {candidates}")
    else:
        print("\nAll mapped voices are valid!")


if __name__ == "__main__":
    asyncio.run(main())