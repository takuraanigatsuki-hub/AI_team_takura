"""Генерация CSS-темы из Figma (Snow Dashboard UI Kit) + fallback SnowUI tokens."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

# Официальные токены SnowUI (https://github.com/SnowUI/home)
SNOW_OFFICIAL = {
    "light": {
        "bg": "#F9F9FA",
        "surface": "#FFFFFF",
        "surface_2": "#F9F9FA",
        "surface_active": "#EDEEFC",
        "surface_accent": "#E6F1FD",
        "border": "rgba(0, 0, 0, 0.1)",
        "text": "#000000",
        "text_muted": "rgba(0, 0, 0, 0.45)",
        "accent": "#4C98FD",
        "accent_soft": "rgba(76, 152, 253, 0.12)",
        "green": "#71DD8C",
        "purple": "#B899EB",
        "indigo": "#ADADFB",
        "blue": "#7DBBFF",
        "red": "#FF4747",
        "orange": "#FFB55B",
        "yellow": "#FFCC00",
    },
    "dark": {
        "bg": "#333333",
        "surface": "#3A3A3A",
        "surface_2": "rgba(255, 255, 255, 0.06)",
        "surface_active": "rgba(173, 173, 251, 0.14)",
        "surface_accent": "rgba(125, 187, 255, 0.1)",
        "border": "rgba(255, 255, 255, 0.12)",
        "text": "#FFFFFF",
        "text_muted": "rgba(255, 255, 255, 0.55)",
        "accent": "#ADADFB",
        "accent_soft": "rgba(173, 173, 251, 0.14)",
        "green": "#71DD8C",
        "purple": "#B899EB",
        "indigo": "#ADADFB",
        "blue": "#7DBBFF",
        "red": "#FF4747",
        "orange": "#FFB55B",
        "yellow": "#FFCC00",
    },
}

SNOW_FIGMA_URLS = [
    "https://www.figma.com/design/98CeoEdS4ajrBW8hRjbTb7/Snow-Dashboard-UI-Kit--Preview-?node-id=16-13406",
    "https://www.figma.com/design/pTTWqClVP5NPzmImOUiPn3/Snow-Dashboard-UI-Kit--Preview-?node-id=1445-10218",
]

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "figma-snow-theme.json")
CSS_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "css", "figma-theme.generated.css")


FIGMA_BRAND_COLORS = frozenset({
    "#0acf83", "#a259ff", "#f25022", "#ff7262", "#1abcfe",
})
SNOW_SIGNATURE_COLORS = frozenset({
    "#f9f9fa", "#edeefc", "#e6f1fd", "#4c98fd", "#adadfb", "#7dbbff", "#b899eb",
})


def _hex_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 0.5
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _pick_semantic_colors(colors: list[str]) -> dict[str, str]:
    """Эвристика: частые цвета из макета → semantic tokens."""
    uniq = []
    seen = set()
    for c in colors:
        c = c.lower()
        if c not in seen:
            seen.add(c)
            uniq.append(c)

    light = sorted([c for c in uniq if _hex_luminance(c) > 0.75], key=_hex_luminance, reverse=True)
    dark = sorted([c for c in uniq if _hex_luminance(c) < 0.35], key=_hex_luminance)
    mid = [c for c in uniq if 0.35 <= _hex_luminance(c) <= 0.75]

    accent_candidates = [c for c in mid + uniq if re.match(r"^#[0-9a-f]{6}$", c)]
    accent = next((c for c in accent_candidates if any(x in c for x in ("4c98", "7dbb", "adad", "4f7d"))), None)
    if not accent and mid:
        accent = mid[0]
    if not accent:
        accent = SNOW_OFFICIAL["light"]["accent"]

    return {
        "surface": light[0] if light else SNOW_OFFICIAL["light"]["surface"],
        "bg": light[1] if len(light) > 1 else (light[0] if light else SNOW_OFFICIAL["light"]["bg"]),
        "text": dark[0] if dark else SNOW_OFFICIAL["light"]["text"],
        "accent": accent,
    }


def merge_figma_colors(raw: dict) -> dict:
    """Объединяет цвета из Figma API с официальными Snow токенами."""
    merged = {
        "source": raw.get("source", "snowui-official"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "figma_urls": SNOW_FIGMA_URLS,
        "light": dict(SNOW_OFFICIAL["light"]),
        "dark": dict(SNOW_OFFICIAL["dark"]),
        "extracted": {},
    }

    all_colors: list[str] = []
    for src in raw.get("sources", []):
        if src.get("status") == 200 and src.get("colors"):
            merged["extracted"][src.get("file_key", "?")] = {
                "node_id": src.get("node_id"),
                "root_name": src.get("root_name"),
                "colors": src.get("colors", [])[:24],
            }
            all_colors.extend(src.get("colors", []))

    if all_colors:
        ui_colors = [c.lower() for c in all_colors if c.lower() not in FIGMA_BRAND_COLORS]
        has_snow_signature = any(c in SNOW_SIGNATURE_COLORS for c in ui_colors)
        if has_snow_signature and len(ui_colors) >= 3:
            picked = _pick_semantic_colors(ui_colors)
            merged["source"] = "figma+official"
            merged["light"]["surface"] = picked.get("surface") or merged["light"]["surface"]
            if picked.get("bg") and picked["bg"].lower() != "#ffffff":
                merged["light"]["bg"] = picked["bg"]
            elif (picked.get("surface") or "").lower() == "#ffffff":
                merged["light"]["bg"] = SNOW_OFFICIAL["light"]["bg"]
            if picked.get("text"):
                merged["light"]["text"] = picked["text"]
            if picked.get("accent"):
                merged["light"]["accent"] = picked["accent"]
                r, g, b = int(picked["accent"][1:3], 16), int(picked["accent"][3:5], 16), int(picked["accent"][5:7], 16)
                merged["light"]["accent_soft"] = f"rgba({r}, {g}, {b}, 0.12)"
        else:
            merged["source"] = "snowui-official"

    return merged


def build_css(theme: dict) -> str:
    light = theme["light"]
    dark = theme["dark"]
    src = theme.get("source", "unknown")
    updated = theme.get("updated_at", "")

    def block(mode: str, t: dict) -> str:
        return f"""[data-theme="{mode}"] {{
    --bg: {t['bg']};
    --surface: {t['surface']};
    --surface-2: {t['surface_2']};
    --border: {t['border']};
    --text: {t['text']};
    --text-muted: {t['text_muted']};
    --accent: {t['accent']};
    --accent-text: #fff;
    --accent-soft: {t['accent_soft']};
    --green: {t['green']};
    --purple: {t['purple']};
    --purple-soft: rgba({int(t['purple'][1:3],16)}, {int(t['purple'][3:5],16)}, {int(t['purple'][5:7],16)}, 0.14);
    --red: {t['red']};
    --yellow: {t['yellow']};
    --user-bg: {t['surface_accent']};
    --user-border: {t['accent_soft']};
    --code-bg: {t['surface_2']};
    --glass: {t['surface']}e0;
    --snow-bg-4: {t['surface_active']};
    --snow-bg-5: {t['surface_accent']};
    --snow-logo: {light['accent']};
    --snow-indigo: {t['indigo']};
    --snow-blue: {t['blue']};
    --snow-purple: {t['purple']};
    --snow-green: {t['green']};
    --snow-red: {t['red']};
    --snow-orange: {t['orange']};
}}"""

    return f"""/* Auto-generated Figma/Snow theme — source: {src} — {updated} */
{block('light', light)}

{block('dark', dark)}
"""


def load_theme_data() -> dict:
    if os.path.isfile(DATA_PATH):
        try:
            with open(DATA_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            if "light" in raw and "dark" in raw:
                return raw
            return merge_figma_colors(raw)
        except Exception:
            pass
    return merge_figma_colors({"sources": [], "source": "snowui-official"})


def save_theme(theme: dict) -> None:
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(theme, f, ensure_ascii=False, indent=2)
    css = build_css(theme)
    os.makedirs(os.path.dirname(CSS_PATH), exist_ok=True)
    with open(CSS_PATH, "w", encoding="utf-8") as f:
        f.write(css)


def ensure_theme_files() -> dict:
    theme = load_theme_data()
    if not os.path.isfile(CSS_PATH):
        save_theme(theme)
    return theme


def extract_colors_from_node(node: dict, depth: int = 0, max_depth: int = 8) -> list[str]:
    counts: dict[str, int] = {}

    def walk(n: dict, d: int = 0) -> None:
        if d > max_depth:
            return
        for fill in n.get("fills") or []:
            if fill.get("type") == "SOLID" and fill.get("visible", True) and fill.get("color"):
                c = fill["color"]
                hex_c = f"#{int(c.get('r', 0) * 255):02x}{int(c.get('g', 0) * 255):02x}{int(c.get('b', 0) * 255):02x}"
                counts[hex_c] = counts.get(hex_c, 0) + 1
        for child in n.get("children") or []:
            walk(child, d + 1)

    walk(node)
    return sorted(counts.keys(), key=lambda x: -counts[x])


async def sync_from_figma(urls: Optional[list[str]] = None) -> dict:
    """Импорт цветов из Figma URL → JSON + generated CSS."""
    import asyncio
    import httpx
    from config import config
    from integrations.figma_client import parse_figma_url

    urls = urls or SNOW_FIGMA_URLS
    token = config.get("figma_access_token", "")
    if not token:
        theme = merge_figma_colors({"sources": [], "source": "snowui-official-no-token"})
        save_theme(theme)
        return theme

    sources = []
    async with httpx.AsyncClient(timeout=60) as client:
        for url in urls:
            parsed = parse_figma_url(url)
            if not parsed or not parsed.get("node_id"):
                continue
            fk = parsed["file_key"]
            nid = parsed["node_id"]
            await asyncio.sleep(2.5)
            try:
                resp = await client.get(
                    f"https://api.figma.com/v1/files/{fk}/nodes",
                    headers={"X-Figma-Token": token},
                    params={"ids": nid, "depth": 6},
                )
                entry: dict[str, Any] = {
                    "file_key": fk,
                    "node_id": nid,
                    "url": url,
                    "status": resp.status_code,
                }
                if resp.status_code == 200:
                    doc = resp.json().get("nodes", {}).get(nid, {}).get("document", {})
                    entry["root_name"] = doc.get("name", "")
                    colors = extract_colors_from_node(doc)
                    entry["colors"] = colors
                    counts = {}
                    for c in colors:
                        counts[c] = counts.get(c, 0) + 1
                    entry["color_counts"] = {c: counts[c] for c in colors[:20]}
                else:
                    entry["error"] = resp.text[:200]
                sources.append(entry)
            except Exception as e:
                sources.append({"url": url, "status": 0, "error": str(e)})

    theme = merge_figma_colors({"sources": sources})
    save_theme(theme)
    return theme
