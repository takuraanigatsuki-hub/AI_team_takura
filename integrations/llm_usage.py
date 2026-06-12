"""Учёт использования LLM (токены / примерная стоимость)."""

import json
import os
from datetime import datetime

USAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "llm_usage.json")

# USD per 1M tokens (approx gpt-4o-mini)
COST_PER_1M_INPUT = 0.15
COST_PER_1M_OUTPUT = 0.60


def _load() -> dict:
    if not os.path.exists(USAGE_FILE):
        return {"total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0, "by_day": {}}
    try:
        with open(USAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"total_requests": 0, "total_input_tokens": 0, "total_output_tokens": 0, "by_day": {}}


def _save(data: dict) -> None:
    os.makedirs(os.path.dirname(os.path.dirname(USAGE_FILE)), exist_ok=True)
    with open(USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_usage(input_tokens: int = 0, output_tokens: int = 0, model: str = "") -> None:
    data = _load()
    data["total_requests"] = data.get("total_requests", 0) + 1
    data["total_input_tokens"] = data.get("total_input_tokens", 0) + input_tokens
    data["total_output_tokens"] = data.get("total_output_tokens", 0) + output_tokens
    day = datetime.now().strftime("%Y-%m-%d")
    by_day = data.setdefault("by_day", {})
    day_entry = by_day.setdefault(day, {"requests": 0, "input": 0, "output": 0})
    day_entry["requests"] += 1
    day_entry["input"] += input_tokens
    day_entry["output"] += output_tokens
    data["last_model"] = model
    _save(data)


def estimate_cost(data: dict = None) -> float:
    data = data or _load()
    inp = data.get("total_input_tokens", 0)
    out = data.get("total_output_tokens", 0)
    return round((inp / 1_000_000 * COST_PER_1M_INPUT) + (out / 1_000_000 * COST_PER_1M_OUTPUT), 4)


def get_stats() -> dict:
    data = _load()
    return {
        **data,
        "estimated_cost_usd": estimate_cost(data),
        "estimated_cost_rub": round(estimate_cost(data) * 95, 2),
    }
