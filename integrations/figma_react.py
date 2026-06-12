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


def _tokens_from_summary(summary: dict) -> dict:
    """Design tokens из Figma summary → CSS-переменные для React inline styles."""
    colors = summary.get("colors") or []
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
    }
    if colors:
        defaults["accent"] = colors[0]
        if len(colors) > 1:
            defaults["accent2"] = colors[1]
        if len(colors) > 2:
            defaults["surface"] = colors[2]
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
  gradient: 'linear-gradient(135deg, __ACCENT__ 0%, __ACCENT2__ 50%, __SUCCESS__ 100%)',
};
const task = "__TASK__";

const styles = {
  page: { minHeight: '100vh', background: tokens.bg, color: tokens.text, fontFamily: "'Inter', system-ui, sans-serif", lineHeight: 1.5 },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 32px', borderBottom: `1px solid ${tokens.border}`, position: 'sticky', top: 0, background: 'rgba(11,13,18,0.92)', backdropFilter: 'blur(12px)', zIndex: 100, flexWrap: 'wrap', gap: 12 },
  logo: { display: 'flex', alignItems: 'center', gap: 10, fontWeight: 700, fontSize: 18 },
  logoMark: { width: 32, height: 32, borderRadius: 8, background: tokens.gradient, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 },
  nav: { display: 'flex', gap: 24 },
  navLink: { color: tokens.muted, fontSize: 14, textDecoration: 'none', cursor: 'pointer' },
  headerActions: { display: 'flex', gap: 8 },
  btnGhost: { background: 'transparent', color: tokens.text, border: `1px solid ${tokens.border}`, borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 500, cursor: 'pointer' },
  btnPrimary: { background: tokens.accent, color: '#fff', border: 'none', borderRadius: 8, padding: '8px 16px', fontSize: 14, fontWeight: 500, cursor: 'pointer' },
  hero: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 48, padding: '72px 32px 80px', maxWidth: 1200, margin: '0 auto', alignItems: 'center', position: 'relative' },
  heroGlow: { position: 'absolute', top: -80, right: '10%', width: 480, height: 480, background: 'radial-gradient(circle, rgba(108,99,255,0.22) 0%, transparent 70%)', pointerEvents: 'none' },
  badge: { display: 'inline-block', background: 'rgba(108,99,255,0.15)', color: tokens.accent2, padding: '6px 14px', borderRadius: 999, fontSize: 12, fontWeight: 600, marginBottom: 20, border: '1px solid rgba(108,99,255,0.25)' },
  heroTitle: { fontSize: 'clamp(34px, 5vw, 54px)', fontWeight: 800, lineHeight: 1.08, marginBottom: 18, letterSpacing: '-0.02em', margin: '0 0 18px' },
  gradientText: { background: tokens.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' },
  lead: { color: tokens.muted, fontSize: 18, maxWidth: 500, marginBottom: 32, lineHeight: 1.65 },
  heroCta: { display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 36 },
  btnXl: { background: tokens.gradient, color: '#fff', border: 'none', borderRadius: 10, padding: '14px 28px', fontSize: 16, fontWeight: 600, cursor: 'pointer' },
  btnXlOutline: { border: `1px solid ${tokens.border}`, borderRadius: 10, padding: '14px 28px', fontSize: 16, color: tokens.text, background: tokens.surface, cursor: 'pointer' },
  stats: { display: 'flex', gap: 36, flexWrap: 'wrap' },
  statValue: { fontSize: 26, fontWeight: 700, display: 'block' },
  statLabel: { fontSize: 12, color: tokens.muted, textTransform: 'uppercase', letterSpacing: '0.04em' },
  heroVisual: { position: 'relative' },
  dashboard: { background: tokens.surface, border: `1px solid ${tokens.border}`, borderRadius: 16, overflow: 'hidden', boxShadow: '0 32px 80px rgba(0,0,0,0.45)' },
  dashboardBar: { display: 'flex', gap: 6, padding: '12px 16px', background: '#0a0c10', borderBottom: `1px solid ${tokens.border}` },
  dot: { width: 10, height: 10, borderRadius: '50%', display: 'inline-block' },
  dashboardBody: { padding: 20 },
  dashboardHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  dashboardTitle: { fontSize: 14, fontWeight: 600, margin: 0 },
  dashboardPill: { fontSize: 11, padding: '4px 10px', borderRadius: 999, background: 'rgba(94,207,138,0.15)', color: tokens.success },
  chart: { display: 'flex', alignItems: 'flex-end', gap: 8, height: 100, marginBottom: 16 },
  chartBar: { flex: 1, borderRadius: '4px 4px 0 0', background: `linear-gradient(180deg, ${tokens.accent} 0%, rgba(108,99,255,0.3) 100%)`, minHeight: 20 },
  metrics: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 },
  metric: { background: tokens.surface2, borderRadius: 8, padding: 12, border: `1px solid ${tokens.border}` },
  metricLabel: { fontSize: 11, color: tokens.muted, marginBottom: 4 },
  metricValue: { fontSize: 18, fontWeight: 700 },
  features: { maxWidth: 1200, margin: '0 auto', padding: '80px 32px' },
  sectionLabel: { textAlign: 'center', fontSize: 12, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: tokens.accent2, marginBottom: 12 },
  sectionTitle: { fontSize: 'clamp(28px, 4vw, 36px)', textAlign: 'center', marginBottom: 16, fontWeight: 700 },
  sectionDesc: { textAlign: 'center', color: tokens.muted, maxWidth: 560, margin: '0 auto 48px', fontSize: 16 },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 },
  card: { background: tokens.surface, border: `1px solid ${tokens.border}`, borderRadius: 14, padding: 28 },
  cardIcon: { width: 48, height: 48, borderRadius: 12, background: 'rgba(108,99,255,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, marginBottom: 16 },
  cardTitle: { fontSize: 18, marginBottom: 8, fontWeight: 600, margin: '0 0 8px' },
  cardDesc: { color: tokens.muted, fontSize: 14, lineHeight: 1.6, margin: 0 },
  cta: { maxWidth: 900, margin: '0 auto 80px', padding: '56px 40px', textAlign: 'center', background: tokens.surface, borderRadius: 24, border: `1px solid ${tokens.border}`, position: 'relative', overflow: 'hidden' },
  ctaGlow: { position: 'absolute', top: -60, left: '50%', transform: 'translateX(-50%)', width: 400, height: 200, background: 'radial-gradient(ellipse, rgba(108,99,255,0.2) 0%, transparent 70%)', pointerEvents: 'none' },
  ctaContent: { position: 'relative', zIndex: 1 },
  ctaText: { color: tokens.muted, marginBottom: 28, fontSize: 16 },
  ctaForm: { display: 'flex', gap: 10, maxWidth: 440, margin: '0 auto', flexWrap: 'wrap', justifyContent: 'center' },
  input: { flex: 1, minWidth: 200, background: tokens.bg, border: `1px solid ${tokens.border}`, borderRadius: 10, padding: '12px 16px', color: tokens.text, fontSize: 14 },
  ctaNote: { marginTop: 14, fontSize: 12, color: tokens.muted },
  footer: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '24px 32px', borderTop: `1px solid ${tokens.border}`, color: tokens.muted, fontSize: 13, flexWrap: 'wrap', gap: 12 },
  footerLinks: { display: 'flex', gap: 20 },
  footerLink: { color: tokens.muted, textDecoration: 'none' },
  toast: { position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)', background: tokens.surface, border: `1px solid ${tokens.success}`, color: tokens.success, padding: '12px 24px', borderRadius: 10, fontSize: 14, fontWeight: 500, zIndex: 200 },
  figmaNote: { textAlign: 'center', fontSize: 11, color: tokens.muted, padding: '8px 16px 24px', opacity: 0.7 },
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
