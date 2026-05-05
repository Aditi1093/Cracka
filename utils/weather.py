"""
utils/weather.py
Real-time weather using OpenWeatherMap API.
Get free API key at: https://openweathermap.org/api
Set: OPENWEATHER_KEY in environment or config.json
"""

import os
import requests
import json
from core.logger import log_error


def _get_api_key() -> str:
    # Try environment variable first
    key = os.environ.get("OPENWEATHER_KEY", "")
    if key:
        return key
    # Try config file
    if os.path.exists("data/config.json"):
        try:
            with open("data/config.json") as f:
                return json.load(f).get("openweather_key", "")
        except Exception:
            pass
    return ""


def get_weather(city: str = "Pune") -> str:
    """Get current weather for a city."""
    api_key = _get_api_key()
    if not api_key:
        return ("Weather API key not set Boss. "
                "Get a free key from openweathermap.org and set OPENWEATHER_KEY in environment.")

    try:
        url = (f"https://api.openweathermap.org/data/2.5/weather"
               f"?q={city}&appid={api_key}&units=metric")
        r = requests.get(url, timeout=5)
        data = r.json()

        if data.get("cod") != 200:
            return f"City '{city}' not found Boss. Please check the city name."

        temp = data["main"]["temp"]
        feels = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        desc = data["weather"][0]["description"].capitalize()
        wind = data["wind"]["speed"]
        city_name = data["name"]
        country = data["sys"]["country"]

        return (f"Weather in {city_name}, {country}: {desc}. "
                f"Temperature {temp:.0f}°C, feels like {feels:.0f}°C. "
                f"Humidity {humidity}%, wind {wind} m/s.")

    except requests.exceptions.Timeout:
        return "Weather service timed out Boss."
    except Exception as e:
        log_error(f"Weather error: {e}")
        return "Could not get weather Boss. Check your internet connection."


def get_forecast(city: str = "Pune", days: int = 3) -> str:
    """Get weather forecast for next N days."""
    api_key = _get_api_key()
    if not api_key:
        return "Weather API key not set Boss."

    try:
        url = (f"https://api.openweathermap.org/data/2.5/forecast"
               f"?q={city}&appid={api_key}&units=metric&cnt={days * 8}")
        r = requests.get(url, timeout=5)
        data = r.json()

        if data.get("cod") != "200":
            return f"Could not get forecast for {city} Boss."

        # Get one reading per day (every 8th = 24 hours apart)
        lines = [f"Forecast for {city}:"]
        seen_dates = set()
        for item in data["list"]:
            date = item["dt_txt"].split(" ")[0]
            if date not in seen_dates:
                seen_dates.add(date)
                desc = item["weather"][0]["description"]
                temp = item["main"]["temp"]
                lines.append(f"  {date}: {desc}, {temp:.0f}°C")
            if len(seen_dates) >= days:
                break

        return "\n".join(lines)

    except Exception as e:
        log_error(f"Forecast error: {e}")
        return "Could not get forecast Boss."