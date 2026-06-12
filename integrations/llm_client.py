"""OpenAI-compatible LLM — реальные ответы агентов + streaming."""

import os
from typing import AsyncIterator, Optional

import httpx


def is_configured() -> bool:
    import config as cfg
    key = os.environ.get("OPENAI_API_KEY") or cfg.config.get("openai_api_key", "")
    return bool(key.strip())


def _settings() -> dict:
    import config as cfg
    return {
        "api_key": os.environ.get("OPENAI_API_KEY") or cfg.config.get("openai_api_key", ""),
        "base_url": (os.environ.get("OPENAI_BASE_URL") or cfg.config.get("openai_base_url")
                     or "https://api.openai.com/v1").rstrip("/"),
        "model": os.environ.get("LLM_MODEL") or cfg.config.get("llm_model") or "gpt-4o-mini",
    }


async def chat(messages: list, max_tokens: int = 800) -> str:
    cfg = _settings()
    if not cfg["api_key"]:
        return ""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
            json={"model": cfg["model"], "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"LLM {resp.status_code}: {resp.text[:300]}")
        data = resp.json()
        try:
            from integrations.llm_usage import record_usage
            usage = data.get("usage") or {}
            record_usage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                model=cfg["model"],
            )
        except Exception:
            pass
        return data["choices"][0]["message"]["content"]


async def chat_stream(messages: list, max_tokens: int = 900) -> AsyncIterator[str]:
    cfg = _settings()
    if not cfg["api_key"]:
        return
    async with httpx.AsyncClient(timeout=90.0) as client:
        async with client.stream(
            "POST",
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"},
            json={"model": cfg["model"], "messages": messages, "max_tokens": max_tokens,
                  "temperature": 0.7, "stream": True},
        ) as resp:
            if resp.status_code != 200:
                body = await resp.aread()
                raise RuntimeError(f"LLM stream {resp.status_code}: {body[:300]}")
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                payload = line[6:].strip()
                if payload == "[DONE]":
                    break
                try:
                    import json
                    chunk = json.loads(payload)
                    delta = chunk["choices"][0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
                except Exception:
                    continue


async def agent_reply(agent_name: str, role: str, system: str, task: str, knowledge: list) -> str:
    ctx = ""
    if knowledge:
        ctx = "\n".join(f"- {k.get('title', k.get('topic', ''))}: {k.get('summary', '')[:120]}"
                          for k in knowledge[:3])
    messages = [
        {"role": "system", "content": f"Ты {agent_name}, {role}. {system}\nОтвечай на русском, кратко и по делу."},
        {"role": "user", "content": f"Задача: {task}\n\nКонтекст из базы знаний:\n{ctx or '—'}"},
    ]
    return await chat(messages)
