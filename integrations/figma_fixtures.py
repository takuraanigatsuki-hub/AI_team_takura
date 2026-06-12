"""Локальные фикстуры Figma — fallback при отсутствии API-токена."""

import json
import os
from typing import Optional

_FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "figma_imports")


def get_fixture(file_key: str) -> Optional[dict]:
    """Загрузить сохранённый импорт макета по file_key."""
    if not file_key:
        return None
    path = os.path.join(_FIXTURES_DIR, f"{file_key}.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def list_fixture_keys() -> list[str]:
    if not os.path.isdir(_FIXTURES_DIR):
        return []
    keys = []
    for name in os.listdir(_FIXTURES_DIR):
        if name.endswith(".json"):
            keys.append(name[:-5])
    return sorted(keys)
