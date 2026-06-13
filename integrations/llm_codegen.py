"""Генерация UI/артефактов через LLM — без готовых шаблонов."""

import logging
import re

log = logging.getLogger(__name__)

_CODE_MARKERS = ("function App", "const App", "export default function App")


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:120]


async def generate_react_from_llm(task_text: str, hints: dict = None) -> dict:
    """React-компонент от LLM; при сбое — богатый шаблон из react_preview."""
    hints = hints or {}
    title = (task_text or "Компонент")[:60]
    from room.task_routing import classify_task_kind, should_export_site

    is_site = classify_task_kind(task_text) == "site" or should_export_site(task_text)

    try:
        from integrations.llm_client import is_configured, agent_reply
        if is_configured():
            extra = hints.get("prompt_extra") or ""
            site_rules = (
                "Это одностраничный сайт: навигация только якоря #section или кнопки, "
                "НЕ используй href=\"/\" и href=\"#\" — они уводят с страницы. "
                "Секции помечай id=\"about\", id=\"services\" и т.д."
            ) if is_site else ""
            prompt = (
                f"Сгенерируй один React-компонент function App() для задачи:\n{task_text}\n\n"
                f"{extra}\n{site_rules}\n\n"
                "Только JSX+useState, inline styles, без import. "
                "Уникальный дизайн под задачу, не generic landing. "
                "Верни только код компонента."
            )
            last_err = None
            for attempt in range(2):
                try:
                    raw = await agent_reply(
                        "Соня", "Frontend Developer",
                        "Эксперт React UI", prompt, [],
                        max_tokens=8192,
                        timeout=120.0,
                    )
                    code = _extract_code(raw)
                    if code and any(marker in code for marker in _CODE_MARKERS):
                        result = {"title": title, "code": code, "generated_by": "llm"}
                        if is_site:
                            result["is_site"] = True
                        return result
                    last_err = "LLM вернул код без App()"
                except Exception as exc:
                    last_err = str(exc)
                    log.warning("LLM codegen attempt %s failed: %s", attempt + 1, exc)
            if last_err:
                log.warning("LLM codegen fallback for task %r: %s", title, last_err)
    except Exception as exc:
        log.warning("LLM codegen unavailable: %s", exc)

    result = _template_react(task_text, hints)
    if is_site:
        result["is_site"] = True
    return result


async def generate_artifact_content(task_text: str, art_type: str, agent_name: str, hints: dict = None) -> str:
    """Текст/HTML арtefact от LLM."""
    hints = hints or {}
    try:
        from integrations.llm_client import is_configured, agent_reply
        if is_configured():
            prompt = (
                f"Задача ({art_type}): {task_text}\n"
                f"{hints.get('prompt_extra', '')}\n"
                "Создай уникальный результат под запрос. "
                "Для presentation/table — HTML или markdown. Для code — блок кода."
            )
            return await agent_reply(
                agent_name, art_type, "Expert", prompt, [],
                max_tokens=4096,
                timeout=90.0,
            )
    except Exception as exc:
        log.warning("LLM artifact generation failed: %s", exc)
    return f"Результат по задаче: {task_text}"


def _extract_code(text: str) -> str:
    m = re.search(r"```(?:jsx|javascript|js|tsx)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    text = (text or "").strip()
    for marker in _CODE_MARKERS:
        if marker in text:
            return text[text.find(marker):].strip()
    return ""


def _template_react(task_text: str, hints: dict | None = None) -> dict:
    """Fallback — полноценный шаблон под тип задачи, не пустой каркас."""
    hints = hints or {}
    try:
        from agents.react_preview import generate_react_preview

        colors = hints.get("colors") or None
        theme = hints.get("theme") or ""
        preview = generate_react_preview(task_text, theme=theme, colors=colors)
        preview["generated_by"] = "template"
        return preview
    except Exception as exc:
        log.warning("Template react fallback failed: %s", exc)

    title = (task_text or "Компонент")[:60]
    code = f"""
function App() {{
  const [note] = useState("{_esc(task_text)}");
  return (
    <div style={{{{ minHeight: '100vh', padding: 32, fontFamily: 'system-ui',
      background: 'linear-gradient(160deg,#1a1d2e,#252a40)', color: '#f0f0f5' }}}}>
      <h1 style={{{{ fontSize: 28, marginBottom: 12, fontWeight: 700 }}}}>{_esc(title)}</h1>
      <p style={{{{ opacity: 0.85, lineHeight: 1.6, maxWidth: 640 }}}}>{{note}}</p>
    </div>
  );
}}
"""
    return {"title": title, "code": code, "generated_by": "minimal"}
