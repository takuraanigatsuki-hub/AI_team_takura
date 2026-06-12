"""Генерация UI/артефактов через LLM — без готовых шаблонов."""

import re


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")[:120]


async def generate_react_from_llm(task_text: str, hints: dict = None) -> dict:
    """React-компонент от LLM; минимальный fallback без библиотеки шаблонов."""
    hints = hints or {}
    title = (task_text or "Компонент")[:60]

    try:
        from integrations.llm_client import is_configured, agent_reply
        if is_configured():
            extra = hints.get("prompt_extra") or ""
            prompt = (
                f"Сгенерируй один React-компонент function App() для задачи:\n{task_text}\n\n"
                f"{extra}\n\n"
                "Только JSX+useState, inline styles, без import. "
                "Уникальный дизайн под задачу, не generic landing. "
                "Верни только код компонента."
            )
            code = await agent_reply(
                "Соня", "Frontend Developer",
                "Эксперт React UI", prompt, [],
            )
            code = _extract_code(code)
            if code and "function App" in code:
                return {"title": title, "code": code, "generated_by": "llm"}
    except Exception:
        pass

    return _minimal_react(title, task_text)


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
            return await agent_reply(agent_name, art_type, "Expert", prompt, [])
    except Exception:
        pass
    return f"Результат по задаче: {task_text}"


def _extract_code(text: str) -> str:
    m = re.search(r"```(?:jsx|javascript|js)?\s*([\s\S]*?)```", text)
    if m:
        return m.group(1).strip()
    if "function App" in text:
        return text.strip()
    return ""


def _minimal_react(title: str, task: str) -> dict:
    """Единственный fallback — простой блок, не landing."""
    code = f"""
function App() {{
  const [note] = useState("{_esc(task)}");
  return (
    <div style={{{{ minHeight: '100vh', padding: 32, fontFamily: 'system-ui',
      background: 'linear-gradient(160deg,#1a1d2e,#252a40)', color: '#f0f0f5' }}}}>
      <h1 style={{{{ fontSize: 24, marginBottom: 12 }}}}>{_esc(title)}</h1>
      <p style={{{{ opacity: 0.85, lineHeight: 1.6 }}}}>{{note}}</p>
      <div style={{{{ marginTop: 24, padding: 20, background: 'rgba(255,255,255,0.06)',
        borderRadius: 12, border: '1px solid rgba(255,255,255,0.12)' }}}}>
        Сгенерировано под вашу задачу (LLM недоступен — базовый каркас).
      </div>
    </div>
  );
}}
"""
    return {"title": title, "code": code, "generated_by": "minimal"}
