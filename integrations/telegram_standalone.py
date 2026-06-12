"""
Standalone Telegram bot — работает через HTTP API сервера.
Запуск (в отдельном терминале, когда main.py уже работает):

  python integrations/telegram_standalone.py
"""
import asyncio
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config  # noqa: F401

API_BASE = os.environ.get("APP_API_URL", "http://127.0.0.1:8000")


class _AgentProxy:
    def __init__(self, state: dict):
        self._state = state
        self.agent_id = state.get("agent_id", "")
        self.name = state.get("name", "")
        self.emoji = state.get("emoji", "")
        self.status = state.get("status", "idle")

    def get_state(self):
        return self._state


class _TaskHistoryProxy:
    def __init__(self, data: dict):
        self._data = data

    def stats(self):
        return self._data.get("stats", {})

    def get_all(self):
        return self._data.get("tasks", [])


class HttpRoom:
    """Прокси к REST API вместо in-process RoomManager."""

    def __init__(self):
        self.agents = {}
        self.task_history = _TaskHistoryProxy({})
        self.work_history = []
        self.pipeline = type("P", (), {"get_state": lambda self: None})()

    async def refresh_from_api(self):
        import httpx
        async with httpx.AsyncClient(timeout=20, trust_env=False) as c:
            tr = await c.get(f"{API_BASE}/api/tasks")
            ar = await c.get(f"{API_BASE}/api/agents")
            task_data = tr.json() if tr.status_code == 200 else {}
            self.task_history = _TaskHistoryProxy(task_data)
            agents_list = ar.json().get("agents", []) if ar.status_code == 200 else []
            self.agents = {a["agent_id"]: _AgentProxy(a) for a in agents_list}

    async def handle_user_message(self, data: dict):
        import httpx
        text = data.get("text", "")
        if text.startswith("[Telegram]"):
            text = text.replace("[Telegram]", "", 1).strip()
        payload = {"text": text, "target": data.get("target", "all")}
        async with httpx.AsyncClient(timeout=20, trust_env=False) as c:
            await c.post(f"{API_BASE}/api/webhook/task", json=payload)


async def main():
    from integrations.telegram_bot import (
        polling_loop, _prepare_bot, _api, _token, _log,
        send_message, main_reply_keyboard, _handle_command,
    )
    import integrations.telegram_bot as tb

    if not _token():
        print("TELEGRAM_BOT_TOKEN not set in .env")
        return

    me = await _api("getMe")
    if not me.get("ok"):
        print("Invalid token:", me)
        return

    username = me["result"]["username"]

    import httpx
    try:
        async with httpx.AsyncClient(timeout=3, trust_env=False) as c:
            r = await c.get(f"{API_BASE}/api/agents")
            if r.status_code != 200:
                print(f"Server {API_BASE} not ready (HTTP {r.status_code}). Start main.py first!")
                return
    except Exception as e:
        print(f"Server {API_BASE} unreachable: {e}\nStart main.py first!")
        return

    _log(f"standalone @{username} -> {API_BASE}")
    room = HttpRoom()
    await room.refresh_from_api()

    orig_handle = tb._handle_command

    async def handle_with_refresh(chat_id, cmd, rm, message_id=None):
        if hasattr(rm, "refresh_from_api"):
            await rm.refresh_from_api()
        await orig_handle(chat_id, cmd, rm, message_id)

    tb._handle_command = handle_with_refresh

    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.config.get("telegram_chat_id")
    if chat_id:
        await send_message(
            chat_id,
            f"Standalone bot @{username} online.\nServer: {API_BASE}\nTry /ping or buttons.",
            reply_markup=main_reply_keyboard(),
        )

    stop = asyncio.Event()
    await _prepare_bot()
    print(f"Telegram standalone running @{username}. Ctrl+C to stop.")
    await polling_loop(room, stop)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped.")
