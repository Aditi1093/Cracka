"""
core/config_loader.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Cracka AI — Central Config Loader
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Saare modules yahan se settings lete hain.

Usage:
  from core.config_loader import config
  name  = config.get("assistant", "name")
  key   = config.get("apis", "openweather_key")
  speed = config.get("assistant", "voice_speed", default=160)
  if config.feature("gmail_enabled"):
      ...
"""

import json
import os

CONFIG_FILE = "data/config.json"

_cache = None


def _load() -> dict:
    global _cache
    if _cache:
        return _cache
    if not os.path.exists(CONFIG_FILE):
        print(f"[Config] {CONFIG_FILE} not found — using defaults.")
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        return _cache
    except Exception as e:
        print(f"[Config] Load error: {e}")
        return {}


class Config:

    def get(self, section: str, key: str, default=None):
        """Get a value from config. Returns default if not found."""
        data = _load()
        return data.get(section, {}).get(key, default)

    def section(self, section: str) -> dict:
        """Get an entire section as dict."""
        return _load().get(section, {})

    def feature(self, name: str) -> bool:
        """Check if a feature is enabled."""
        return bool(_load().get("features", {}).get(name, False))

    def reload(self):
        """Force reload config from disk."""
        global _cache
        _cache = None
        _load()

    def set(self, section: str, key: str, value):
        """Update a value and save to disk."""
        data = _load()
        if section not in data:
            data[section] = {}
        data[section][key] = value
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        global _cache
        _cache = data


# Singleton — sab yahi use karenge
config = Config()