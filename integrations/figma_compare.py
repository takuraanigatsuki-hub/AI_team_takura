"""Сравнение Figma-макета с React Preview — палитра и score."""

import re
from typing import Optional


def _parse_hex(color: str) -> Optional[tuple]:
    c = (color or "").strip().lower()
    m = re.match(r"^#([0-9a-f]{6})$", c)
    if not m:
        return None
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _color_distance(a: tuple, b: tuple) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def compare_palettes(figma_colors: list, react_colors: list) -> dict:
    figma = [_parse_hex(c) for c in (figma_colors or []) if _parse_hex(c)]
    react = [_parse_hex(c) for c in (react_colors or []) if _parse_hex(c)]

    if not figma or not react:
        return {
            "score": 0,
            "matched": 0,
            "total": len(figma),
            "message": "Недостаточно цветов для сравнения",
        }

    matched = 0
    pairs = []
    used = set()
    for fc in figma[:12]:
        best = None
        best_d = 999
        best_i = -1
        for i, rc in enumerate(react):
            if i in used:
                continue
            d = _color_distance(fc, rc)
            if d < best_d:
                best_d = d
                best = rc
                best_i = i
        if best and best_d < 80:
            matched += 1
            used.add(best_i)
            pairs.append({"figma": f"#{fc[0]:02x}{fc[1]:02x}{fc[2]:02x}", "react": f"#{best[0]:02x}{best[1]:02x}{best[2]:02x}", "delta": round(best_d, 1)})

    score = int(matched / min(len(figma), 8) * 100) if figma else 0
    score = min(100, max(0, score))
    return {
        "score": score,
        "matched": matched,
        "total": min(len(figma), 8),
        "pairs": pairs[:8],
        "figma_colors": [f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in figma[:8]],
        "react_colors": [f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}" for c in react[:8]],
        "message": "Отличное совпадение" if score >= 75 else ("Хорошо" if score >= 45 else "Нужна доработка"),
    }
