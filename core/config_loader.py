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

# FIX: use None as "not loaded yet" sentinel.
# An empty dict {} is a valid loaded config and should NOT trigger reload.
_cache = None


def _load() -> dict:
    global _cache

    # FIX: check "is not None" instead of truthiness
    # (empty dict {} is falsy but IS a valid cached value)
    if _cache is not None:
        return _cache

    if not os.path.exists(CONFIG_FILE):
        print(f"[Config] {CONFIG_FILE} not found — using defaults.")
        _cache = {}
        return _cache

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            _cache = json.load(f)
        return _cache
    except Exception as e:
        print(f"[Config] Load error: {e}")
        _cache = {}
        return _cache


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

        # FIX: ensure data/ folder exists before writing
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Save error: {e}")
            return

        global _cache
        _cache = data


# Singleton — sab yahi use karenge
config = Config()