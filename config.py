import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

_defaults = {
    "host": "0.0.0.0",
    "port": 8000,
    "learning_interval_min": 15,
    "learning_interval_max": 45,
    "learning_sources": ["devto", "hackernews"],
    "persist_knowledge": True,
    "debug": False
}


def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**_defaults, **data}
        except Exception:
            pass
    return _defaults.copy()


config = _load_config()
