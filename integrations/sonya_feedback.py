"""Лайки/дизлайки для обучения Сони — влияют на выбор макетов и проектов."""

import json
import os
from datetime import datetime
from typing import Optional

DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "sonya_feedback.json")


def _ensure() -> None:
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)


def _load() -> dict:
    _ensure()
    if not os.path.exists(DATA_FILE):
        return {"votes": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "votes" in data:
            return data
    except Exception:
        pass
    return {"votes": []}


def _save(data: dict) -> None:
    _ensure()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def record_vote(
    *,
    target_type: str,
    target_id: str,
    vote: int,
    user_id: str = "",
    note: str = "",
) -> dict:
    """vote: +1 like, -1 dislike."""
    if vote not in (1, -1):
        raise ValueError("vote must be 1 or -1")
    if not target_id:
        raise ValueError("target_id required")
    data = _load()
    votes = data.get("votes") or []
    votes = [
        v for v in votes
        if not (v.get("target_type") == target_type and v.get("target_id") == target_id
                and v.get("user_id", "") == (user_id or ""))
    ]
    entry = {
        "target_type": target_type,
        "target_id": target_id,
        "vote": vote,
        "user_id": user_id or "",
        "note": (note or "")[:200],
        "timestamp": datetime.now().isoformat(),
    }
    votes.insert(0, entry)
    data["votes"] = votes[:500]
    _save(data)
    return entry


def score(target_type: str, target_id: str) -> int:
    total = 0
    for v in _load().get("votes") or []:
        if v.get("target_type") == target_type and v.get("target_id") == target_id:
            total += int(v.get("vote") or 0)
    return total


def user_vote(target_type: str, target_id: str, user_id: str = "") -> int:
    for v in _load().get("votes") or []:
        if (v.get("target_type") == target_type and v.get("target_id") == target_id
                and v.get("user_id", "") == (user_id or "")):
            return int(v.get("vote") or 0)
    return 0


def is_disliked(target_type: str, target_id: str, *, threshold: int = -1) -> bool:
    return score(target_type, target_id) <= threshold


def votes_for_targets(target_type: str, limit: int = 100) -> dict[str, int]:
    out: dict[str, int] = {}
    for v in (_load().get("votes") or [])[:limit * 3]:
        if v.get("target_type") != target_type:
            continue
        tid = v.get("target_id") or ""
        if not tid:
            continue
        out[tid] = out.get(tid, 0) + int(v.get("vote") or 0)
    return out


def filter_disliked_keys(file_keys: list[str]) -> list[str]:
    """Убрать file_key с суммарным дизлайком."""
    scores = votes_for_targets("figma_file", 200)
    return [k for k in file_keys if scores.get(k, 0) > -2]


def feedback_summary(limit: int = 40) -> list[dict]:
    agg: dict[tuple[str, str], dict] = {}
    for v in _load().get("votes") or []:
        key = (v.get("target_type", ""), v.get("target_id", ""))
        if not key[1]:
            continue
        row = agg.setdefault(key, {
            "target_type": key[0],
            "target_id": key[1],
            "score": 0,
            "likes": 0,
            "dislikes": 0,
            "last_at": v.get("timestamp"),
        })
        vote = int(v.get("vote") or 0)
        row["score"] += vote
        if vote > 0:
            row["likes"] += 1
        elif vote < 0:
            row["dislikes"] += 1
    items = sorted(agg.values(), key=lambda x: x.get("last_at") or "", reverse=True)
    return items[:limit]
