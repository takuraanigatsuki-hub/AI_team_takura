from __future__ import annotations

import httpx

from ..core.config import get_settings


class LLMUnavailable(RuntimeError):
    pass


class LLMClient:
    """Минимальный синхронный HTTP-клиент для chat-completions API.

    Поддерживает провайдеров с OpenAI-совместимым API
    (OpenAI, OpenRouter, локальные LM Studio/Ollama-OpenAI shim).

    Имеет два режима генерации:
      - complete(): обычный chat-completion, опционально json mode.
      - complete_with_tools(): native tools API (OpenAI tools / Anthropic
        tool_use через OpenRouter). Возвращает список tool-вызовов.
    """

    def __init__(
        self,
        provider: str,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        provider = provider.lower().strip()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = (
            (base_url.strip() if base_url else "")
            or self._default_base_url(provider)
        ).rstrip("/")

    @staticmethod
    def _default_base_url(provider: str) -> str:
        return {
            "openai": "https://api.openai.com/v1",
            "openrouter": "https://openrouter.ai/api/v1",
        }.get(provider, "https://api.openai.com/v1")

    def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 300,
        response_format_json: bool = False,
    ) -> str:
        if not self.api_key:
            raise LLMUnavailable("LLM API key is not configured")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"network error: {exc}") from exc
        if resp.status_code >= 400:
            raise LLMUnavailable(f"LLM error {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            raise LLMUnavailable(f"unexpected LLM response: {data}") from exc

    def complete_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        tool_choice: str = "auto",
    ) -> dict:
        """Запросить ответ с native tool-calling. Возвращает:

        {
          "content": str | None,       # текст ответа (может быть None если только tool_calls)
          "tool_calls": [
              {"id": str, "name": str, "arguments": dict}, ...
          ],
          "raw": dict,                 # полный choice для дебага
        }

        Если провайдер/модель не поддерживают tools и возвращают 4xx —
        кидаем LLMUnavailable, чтобы выше можно было сделать fallback на JSON-mode.
        """
        if not self.api_key:
            raise LLMUnavailable("LLM API key is not configured")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "tools": tools,
            "tool_choice": tool_choice,
            "parallel_tool_calls": True,
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(
                    f"{self.base_url}/chat/completions", headers=headers, json=payload
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(f"network error: {exc}") from exc
        if resp.status_code >= 400:
            raise LLMUnavailable(
                f"tools LLM error {resp.status_code}: {resp.text[:240]}"
            )
        data = resp.json()
        try:
            choice = data["choices"][0]
            msg = choice["message"]
        except (KeyError, IndexError) as exc:
            raise LLMUnavailable(f"unexpected LLM response: {data}") from exc

        import json as _json

        tool_calls = []
        for tc in msg.get("tool_calls") or []:
            func = tc.get("function") or {}
            raw_args = func.get("arguments", "{}")
            try:
                args = _json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except _json.JSONDecodeError:
                args = {"_raw": raw_args}
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": func.get("name", ""),
                "arguments": args,
            })
        return {
            "content": msg.get("content"),
            "tool_calls": tool_calls,
            "raw": choice,
        }


_singleton: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _singleton
    if _singleton is None:
        settings = get_settings()
        _singleton = LLMClient(
            provider=settings.llm_provider,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            base_url=settings.llm_base_url or None,
        )
    return _singleton


def reset_llm_client() -> None:
    global _singleton
    _singleton = None
