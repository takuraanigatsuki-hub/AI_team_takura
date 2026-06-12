"""Figma → React: генерация UI из импортированного макета."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

_COMPONENTS_DIR = Path(__file__).resolve().parent.parent / "static" / "components"

# Известные Figma Sites / Design файлы → React-компонент
KNOWN_FIGMA_COMPONENTS: dict[str, str] = {
    "uYRfrETGR8pcwChwLtJ6Ua": "LaunchKitLanding.jsx",
}


def _load_component(filename: str) -> str:
    path = _COMPONENTS_DIR / filename
    if path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _strip_component_header(source: str) -> str:
    return re.sub(r"^/\*\*.*?\*/\s*", "", source, count=1, flags=re.DOTALL).strip()


def _esc_js(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:120]


def _parse_hex(color: str) -> Optional[tuple[int, int, int]]:
    c = (color or "").strip().lower()
    m = re.match(r"^#([0-9a-f]{6})$", c)
    if not m:
        return None
    h = m.group(1)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hex_to_rgb_str(color: str, fallback: str = "108, 99, 255") -> str:
    rgb = _parse_hex(color)
    if not rgb:
        return fallback
    return f"{rgb[0]}, {rgb[1]}, {rgb[2]}"


def _luminance(color: str) -> float:
    rgb = _parse_hex(color)
    if not rgb:
        return 0.5
    r, g, b = [c / 255.0 for c in rgb]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturation(color: str) -> float:
    rgb = _parse_hex(color)
    if not rgb:
        return 0.0
    r, g, b = [c / 255.0 for c in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == 0:
        return 0.0
    return (mx - mn) / mx


def _tokens_from_summary(summary: dict) -> dict:
    """Design tokens из Figma summary → inline styles (aligned with startup.css)."""
    colors = summary.get("colors") or []
    fonts = summary.get("fonts") or []
    defaults = {
        "bg": "#0b0d12",
        "surface": "#12151c",
        "surface2": "#1a1e28",
        "border": "#252a36",
        "text": "#e8eaef",
        "muted": "#8b93a7",
        "accent": "#6c63ff",
        "accent2": "#56cfe1",
        "success": "#5ecf8a",
        "font": "Inter",
    }

    parsed = [(c, _luminance(c), _saturation(c)) for c in colors if _parse_hex(c)]
    if parsed:
        by_lum = sorted(parsed, key=lambda x: x[1])
        by_sat = sorted(parsed, key=lambda x: x[2], reverse=True)
        defaults["bg"] = by_lum[0][0]
        if len(by_lum) > 1:
            defaults["surface"] = by_lum[1][0]
        if len(by_lum) > 2:
            defaults["surface2"] = by_lum[2][0]
        if len(by_lum) > 3:
            defaults["border"] = by_lum[3][0]
        vivid = [c for c, _, _ in by_sat if _saturation(c) > 0.15][:3]
        if vivid:
            defaults["accent"] = vivid[0]
            if len(vivid) > 1:
                defaults["accent2"] = vivid[1]
            if len(vivid) > 2:
                defaults["success"] = vivid[2]
        light = [c for c, lum, _ in parsed if lum > 0.7]
        dark_muted = [c for c, lum, _ in parsed if 0.35 < lum < 0.65]
        if light:
            defaults["text"] = light[0]
        if dark_muted:
            defaults["muted"] = dark_muted[0]

    if fonts:
        defaults["font"] = fonts[0].split()[0].strip("'\"") or "Inter"

    defaults["bg_rgb"] = _hex_to_rgb_str(defaults["bg"], "11, 13, 18")
    defaults["accent_rgb"] = _hex_to_rgb_str(defaults["accent"], "108, 99, 255")
    defaults["success_rgb"] = _hex_to_rgb_str(defaults["success"], "94, 207, 138")
    return defaults


_LAUNCHKIT_STYLES = """
const tokens = {
  bg: '__BG__',
  surface: '__SURFACE__',
  surface2: '__SURFACE2__',
  border: '__BORDER__',
  text: '__TEXT__',
  muted: '__MUTED__',
  accent: '__ACCENT__',
  accent2: '__ACCENT2__',
  success: '__SUCCESS__',
  font: '__FONT__',
  gradient: 'linear-gradient(135deg, __ACCENT__ 0%, __ACCENT2__ 50%, __SUCCESS__ 100%)',
  space: { xs: 4, sm: 6, md: 8, lg: 10, xl: 12, '2xl': 14, '3xl': 16, '4xl': 20, '5xl': 24, '6xl': 28, '7xl': 32, '8xl': 36, '9xl': 48, '10xl': 56, '11xl': 72, '12xl': 80 },
  fontSize: { xs: 11, sm: 12, base: 14, md: 16, lg: 18, xl: 26, hero: 'clamp(34px, 5vw, 54px)', section: 'clamp(28px, 4vw, 36px)' },
  radius: { sm: 8, md: 10, lg: 12, xl: 14, '2xl': 16, '3xl': 24, pill: 999 },
};
const task = "__TASK__";

const styles = {
  page: { minHeight: '100vh', background: tokens.bg, color: tokens.text, fontFamily: `'${tokens.font}', system-ui, sans-serif`, lineHeight: 1.5 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: `${tokens.space['3xl']}px ${tokens.space['7xl']}px`, borderBottom: `1px solid ${tokens.border}`, position: 'sticky', top: 0, background: 'rgba(__BG_RGB__, 0.92)', backdropFilter: 'blur(12px)', zIndex: 100, flexWrap: 'wrap', gap: tokens.space.xl },
  logo: { display: 'flex', alignItems: 'center', gap: tokens.space.lg, fontWeight: 700, fontSize: tokens.fontSize.lg },
  logoMark: { width: 32, height: 32, borderRadius: tokens.radius.sm, background: tokens.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: tokens.space['3xl'] },
  nav: { display: 'flex', gap: tokens.space['5xl'] },
  navLink: { color: tokens.muted, fontSize: tokens.fontSize.base, textDecoration: 'none', cursor: 'pointer' },
  headerActions: { display: 'flex', gap: tokens.space.md },
  btnGhost: { background: 'transparent', color: tokens.text, border: `1px solid ${tokens.border}`, borderRadius: tokens.radius.sm, padding: `${tokens.space.md}px ${tokens.space['3xl']}px`, fontSize: tokens.fontSize.base, fontWeight: 500, cursor: 'pointer' },
  btnPrimary: { background: tokens.accent, color: '#fff', border: 'none', borderRadius: tokens.radius.sm, padding: `${tokens.space.md}px ${tokens.space['3xl']}px`, fontSize: tokens.fontSize.base, fontWeight: 500, cursor: 'pointer' },
  hero: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: tokens.space['9xl'], padding: `${tokens.space['11xl']}px ${tokens.space['7xl']}px ${tokens.space['12xl']}px`, maxWidth: 1200, margin: '0 auto', alignItems: 'center', position: 'relative' },
  heroGlow: { position: 'absolute', top: -80, right: '10%', width: 480, height: 480, background: 'radial-gradient(circle, rgba(__ACCENT_RGB__, 0.22) 0%, transparent 70%)', pointerEvents: 'none' },
  badge: { display: 'inline-block', background: 'rgba(__ACCENT_RGB__, 0.15)', color: tokens.accent2, padding: `${tokens.space.sm}px ${tokens.space['2xl']}px`, borderRadius: tokens.radius.pill, fontSize: tokens.fontSize.sm, fontWeight: 600, marginBottom: tokens.space['4xl'], border: '1px solid rgba(__ACCENT_RGB__, 0.25)' },
  heroTitle: { fontSize: tokens.fontSize.hero, fontWeight: 800, lineHeight: 1.08, margin: `0 0 ${tokens.space['2xl']}px`, letterSpacing: '-0.02em' },
  gradientText: { background: tokens.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' },
  lead: { color: tokens.muted, fontSize: tokens.fontSize.lg, maxWidth: 500, marginBottom: tokens.space['7xl'], lineHeight: 1.65 },
  heroCta: { display: 'flex', gap: tokens.space.xl, flexWrap: 'wrap', marginBottom: tokens.space['8xl'] },
  btnXl: { background: tokens.gradient, color: '#fff', border: 'none', borderRadius: tokens.radius.md, padding: `${tokens.space['2xl']}px ${tokens.space['6xl']}px`, fontSize: tokens.fontSize.md, fontWeight: 600, cursor: 'pointer' },
  btnXlOutline: { display: 'inline-flex', alignItems: 'center', border: `1px solid ${tokens.border}`, borderRadius: tokens.radius.md, padding: `${tokens.space['2xl']}px ${tokens.space['6xl']}px`, fontSize: tokens.fontSize.md, color: tokens.text, background: tokens.surface, cursor: 'pointer' },
  stats: { display: 'flex', gap: tokens.space['8xl'], flexWrap: 'wrap' },
  statItem: { display: 'flex', flexDirection: 'column' },
  statValue: { fontSize: tokens.fontSize.xl, fontWeight: 700 },
  statLabel: { fontSize: tokens.fontSize.sm, color: tokens.muted, textTransform: 'uppercase', letterSpacing: '0.04em' },
  heroVisual: { position: 'relative' },
  dashboard: { background: tokens.surface, border: `1px solid ${tokens.border}`, borderRadius: tokens.radius['2xl'], overflow: 'hidden', boxShadow: '0 32px 80px rgba(0,0,0,0.45)' },
  dashboardBar: { display: 'flex', gap: tokens.space.sm, padding: `${tokens.space.xl}px ${tokens.space['3xl']}px`, background: '#0a0c10', borderBottom: `1px solid ${tokens.border}` },
  dot: { width: 10, height: 10, borderRadius: '50%', display: 'inline-block' },
  dashboardBody: { padding: tokens.space['4xl'] },
  dashboardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: tokens.space['4xl'] },
  dashboardTitle: { fontSize: tokens.fontSize.base, fontWeight: 600, margin: 0 },
  dashboardPill: { fontSize: tokens.fontSize.xs, padding: `${tokens.space.xs}px ${tokens.space.lg}px`, borderRadius: tokens.radius.pill, background: 'rgba(__SUCCESS_RGB__, 0.15)', color: tokens.success },
  chart: { display: 'flex', alignItems: 'flex-end', gap: tokens.space.md, height: 100, marginBottom: tokens.space['3xl'] },
  chartBar: { flex: 1, borderRadius: '4px 4px 0 0', background: `linear-gradient(180deg, ${tokens.accent} 0%, rgba(__ACCENT_RGB__, 0.3) 100%)`, minHeight: 20 },
  metrics: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: tokens.space.lg },
  metric: { background: tokens.surface2, borderRadius: tokens.radius.sm, padding: tokens.space.xl, border: `1px solid ${tokens.border}` },
  metricLabel: { fontSize: tokens.fontSize.xs, color: tokens.muted, marginBottom: tokens.space.xs },
  metricValue: { fontSize: tokens.fontSize.lg, fontWeight: 700 },
  features: { maxWidth: 1200, margin: '0 auto', padding: `${tokens.space['12xl']}px ${tokens.space['7xl']}px` },
  sectionLabel: { textAlign: 'center', fontSize: tokens.fontSize.sm, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: tokens.accent2, marginBottom: tokens.space.xl },
  sectionTitle: { fontSize: tokens.fontSize.section, textAlign: 'center', margin: `0 0 ${tokens.space['3xl']}px`, fontWeight: 700 },
  sectionDesc: { textAlign: 'center', color: tokens.muted, maxWidth: 560, margin: `0 auto ${tokens.space['9xl']}px`, fontSize: tokens.fontSize.md },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: tokens.space['4xl'] },
  card: { background: tokens.surface, border: `1px solid ${tokens.border}`, borderRadius: tokens.radius.xl, padding: tokens.space['6xl'] },
  cardIcon: { width: 48, height: 48, borderRadius: tokens.radius.lg, background: 'rgba(__ACCENT_RGB__, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, marginBottom: tokens.space['3xl'] },
  cardTitle: { fontSize: tokens.fontSize.lg, fontWeight: 600, margin: `0 0 ${tokens.space.md}px` },
  cardDesc: { color: tokens.muted, fontSize: tokens.fontSize.base, lineHeight: 1.6, margin: 0 },
  cta: { maxWidth: 900, margin: `0 auto ${tokens.space['12xl']}px`, padding: `${tokens.space['10xl']}px 40px`, textAlign: 'center', background: tokens.surface, borderRadius: tokens.radius['3xl'], border: `1px solid ${tokens.border}`, position: 'relative', overflow: 'hidden' },
  ctaGlow: { position: 'absolute', top: -60, left: '50%', transform: 'translateX(-50%)', width: 400, height: 200, background: 'radial-gradient(ellipse, rgba(__ACCENT_RGB__, 0.2) 0%, transparent 70%)', pointerEvents: 'none' },
  ctaContent: { position: 'relative', zIndex: 1 },
  ctaText: { color: tokens.muted, marginBottom: tokens.space['6xl'], fontSize: tokens.fontSize.md },
  ctaForm: { display: 'flex', gap: tokens.space.lg, maxWidth: 440, margin: '0 auto', flexWrap: 'wrap', justifyContent: 'center' },
  input: { flex: 1, minWidth: 200, background: tokens.bg, border: `1px solid ${tokens.border}`, borderRadius: tokens.radius.md, padding: `${tokens.space.xl}px ${tokens.space['3xl']}px`, color: tokens.text, fontSize: tokens.fontSize.base },
  ctaNote: { marginTop: tokens.space['2xl'], fontSize: tokens.fontSize.sm, color: tokens.muted },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: `${tokens.space['5xl']}px ${tokens.space['7xl']}px`, borderTop: `1px solid ${tokens.border}`, color: tokens.muted, fontSize: 13, flexWrap: 'wrap', gap: tokens.space.xl },
  footerLinks: { display: 'flex', gap: tokens.space['4xl'] },
  footerLink: { color: tokens.muted, textDecoration: 'none' },
  toast: { position: 'fixed', bottom: tokens.space['5xl'], left: '50%', transform: 'translateX(-50%)', background: tokens.surface, border: `1px solid ${tokens.success}`, color: tokens.success, padding: `${tokens.space.xl}px ${tokens.space['5xl']}px`, borderRadius: tokens.radius.md, fontSize: tokens.fontSize.base, fontWeight: 500, zIndex: 200 },
  figmaNote: { textAlign: 'center', fontSize: tokens.fontSize.xs, color: tokens.muted, padding: `${tokens.space.md}px ${tokens.space['3xl']}px ${tokens.space['5xl']}px`, opacity: 0.7 },
};
"""


def _apply_tokens(styles_block: str, tokens: dict) -> str:
    result = styles_block
    for key, value in tokens.items():
        result = result.replace(f"__{key.upper()}__", value)
    return result


def build_launchkit_code(task: str, summary: Optional[dict] = None) -> str:
    """Собрать runnable React-код LaunchKit из компонента и Figma tokens."""
    component = _load_component("LaunchKitLanding.jsx")
    if not component:
        raise FileNotFoundError("LaunchKitLanding.jsx не найден")

    tokens = _tokens_from_summary(summary or {})
    styles = _apply_tokens(_LAUNCHKIT_STYLES, tokens)
    body = _strip_component_header(component)
    return styles.replace('__TASK__', _esc_js(task)) + "\n" + body


def resolve_component_for_file(file_key: str) -> Optional[str]:
    return KNOWN_FIGMA_COMPONENTS.get(file_key)


def refine_react_from_figma(figma_result: dict, task: str = "") -> dict:
    """Доработать React UI по импортированному Figma-макету (цвета, spacing, типографика)."""
    file_key = figma_result.get("file_key", "")
    summary = figma_result.get("summary") or {}
    file_name = summary.get("file_name", "Figma Design")
    component_file = resolve_component_for_file(file_key)
    task_text = task or "Доработай React UI по Figma-макету"

    if component_file == "LaunchKitLanding.jsx":
        code = build_launchkit_code(task_text, summary)
        return {
            "title": "LaunchKit · Figma (refined)",
            "code": code,
            "is_site": True,
            "figma_refined": True,
            "figma_file_key": file_key,
            "figma_url": figma_result.get("url"),
            "colors": summary.get("colors", []),
        }

    preview = generate_react_from_figma(figma_result, task=task_text)
    preview["figma_refined"] = True
    preview["title"] = preview.get("title", file_name) + " (refined)"
    return preview


def generate_react_from_figma(figma_result: dict, task: str = "") -> dict:
    """Сгенерировать React Preview из результата Figma import_design."""
    file_key = figma_result.get("file_key", "")
    summary = figma_result.get("summary") or {}
    file_name = summary.get("file_name", "Figma Design")
    component_file = resolve_component_for_file(file_key)

    task_text = task or f"UI по макету Figma: {file_name}"

    if component_file == "LaunchKitLanding.jsx":
        code = build_launchkit_code(task_text, summary)
        return {
            "title": "LaunchKit · Figma → React",
            "code": code,
            "is_site": True,
            "figma_file_key": file_key,
            "figma_url": figma_result.get("url"),
            "colors": summary.get("colors", []),
        }

    # Generic fallback: landing на основе цветов из Figma
    from agents.react_preview import generate_react_preview

    colors = summary.get("colors", [])
    color_hint = ", ".join(colors[:5]) if colors else ""
    enhanced = f"{task_text}. Цвета: {color_hint}. Адаптивный React-компонент."
    preview = generate_react_preview(enhanced)
    preview["figma_file_key"] = file_key
    preview["figma_url"] = figma_result.get("url")
    preview["colors"] = colors
    return preview
