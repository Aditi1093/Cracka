"""
utils/translator.py
Language translation using deep_translator (free, no API key).
"""

import re
from core.logger import log_error

LANG_CODES = {
    "hindi": "hi", "marathi": "mr", "french": "fr", "spanish": "es",
    "german": "de", "japanese": "ja", "chinese": "zh-CN", "arabic": "ar",
    "portuguese": "pt", "russian": "ru", "italian": "it", "korean": "ko",
    "english": "en", "gujarati": "gu", "tamil": "ta", "telugu": "te",
}


def translate_text(command: str) -> str:
    """
    Translate text from voice command.
    Example: 'translate hello to hindi'
             'translate good morning to french'
    """
    try:
        from deep_translator import GoogleTranslator

        command = command.lower()

        # Find target language
        target_lang = "hi"  # default to Hindi
        for lang_name, code in LANG_CODES.items():
            if lang_name in command:
                target_lang = code
                command = command.replace(lang_name, "")
                break

        # Extract text to translate
        text = command
        for word in ["translate", "to", "into", "in"]:
            text = text.replace(word, "")
        text = text.strip()

        if not text:
            return "Please say what you want to translate Boss."

        translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
        return f"Translation: {translated}"

    except ImportError:
        return "Please install deep_translator: pip install deep-translator"
    except Exception as e:
        log_error(f"Translation error: {e}")
        return f"Translation failed Boss: {e}"