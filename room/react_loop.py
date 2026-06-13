"""ReAct loop: plan → tool → observe → repeat (Фаза C)."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from agents.base_agent import BaseAgent

REACT_AGENT_IDS = {"backend", "qa", "devops", "architect", "security", "cursor"}


def _parse_action(raw: str) -> dict:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        return {"final_answer": text}


async def run_react_for_agent(agent: "BaseAgent", task_text: str, max_steps: int = 5) -> Optional[str]:
    """ReAct-цикл с tools через MCP gateway. None = использовать обычный LLM."""
    import config as cfg
    from integrations.llm_client import is_configured, chat
    from integrations.agent_tools import tools_for
    from integrations.mcp_gateway import invoke_tool

    if not is_configured() or not cfg.config.get("react_enabled", True):
        return None
    if agent.agent_id not in REACT_AGENT_IDS:
        return None

    max_steps = int(cfg.config.get("react_max_steps") or max_steps)
    tools = tools_for(agent.agent_id)
    tool_desc = "\n".join(f"- {t['name']}: {t['description']}" for t in tools)

    history: list[str] = []
    observations: list[dict] = []

    for step in range(max_steps):
        obs_text = ""
        if observations:
            obs_text = "\n\nНаблюдения:\n" + "\n".join(
                f"Step {i + 1} [{o.get('tool')}]: {str(o.get('result', ''))[:600]}"
                for i, o in enumerate(observations[-3:])
            )

        prompt = f"""Ты {agent.name} ({agent.role}). Задача: {task_text}

Доступные tools:
{tool_desc}

Шаг {step + 1}/{max_steps}.{obs_text}

Ответь СТРОГО JSON (без markdown):
{{"thought": "рассуждение", "action": "tool_name или FINISH", "arguments": {{}}, "answer": "если FINISH — финальный ответ пользователю"}}

action=FINISH когда задача решена или нужен только текстовый ответ."""

        raw = await chat(
            [
                {"role": "system", "content": "ReAct agent. Только JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
        )
        action = _parse_action(raw)
        thought = action.get("thought", "")
        act = (action.get("action") or "").strip()

        if agent.room_manager and thought:
            await agent.room_manager.broadcast_work({
                "type": "react_step",
                "agent_id": agent.agent_id,
                "step": step + 1,
                "thought": thought[:300],
                "action": act,
            })

        if act.upper() == "FINISH" or act == "":
            ans = action.get("answer") or action.get("final_answer") or raw
            if ans and str(ans).strip():
                return str(ans).strip()
            break

        result = await invoke_tool(agent.agent_id, act, action.get("arguments") or {})
        observations.append({"tool": act, "result": result})
        history.append(f"{act}: {json.dumps(result, ensure_ascii=False)[:400]}")

    if observations:
        summary = "\n".join(history)
        final = await chat(
            [
                {"role": "system", "content": f"Ты {agent.name}. Сформируй итоговый ответ на русском."},
                {"role": "user", "content": f"Задача: {task_text}\n\nРезультаты tools:\n{summary}"},
            ],
            max_tokens=900,
        )
        return final.strip() if final else None
    return None
