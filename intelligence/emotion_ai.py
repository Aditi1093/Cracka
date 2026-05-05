"""
intelligence/emotion_ai.py
Detect emotion from text using TextBlob sentiment analysis.
"""

from textblob import TextBlob


def detect_emotion(text: str) -> str:
    """
    Analyze sentiment of text.
    Returns: 'happy', 'sad', or 'neutral'
    """
    try:
        analysis = TextBlob(str(text))
        polarity = analysis.sentiment.polarity

        if polarity > 0.3:
            return "happy"
        elif polarity < -0.3:
            return "sad"
        else:
            return "neutral"
    except Exception:
        return "neutral"