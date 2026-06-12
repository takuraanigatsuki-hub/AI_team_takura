"""Telegram Bot — polling, inline-кнопки, управление командой."""

import asyncio
import json
import os
from typing import Optional

CHATS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "telegram_chats.json")
API_BASE = "https://api.telegram.org/bot{token}/{method}"

QUICK_TASKS = {
    "landing": ("frontend", "Сделай landing page для стартапа с hero, features и CTA"),
    "api": ("backend", "Напиши REST API для задач на FastAPI"),
    "ui": ("frontend", "Создай форму регистрации в React"),
    "tests": ("qa", "Напиши smoke-тесты для основных API endpoints"),
    "pitch": ("presenter", "Создай pitch deck на 8 слайдов для стартапа"),
    "3d": ("modeler", "Создай интерактивную 3D hero-сцену для продукта"),
    "all_landing": ("all", "Сделай полный landing page для стартапа — UI, код и deploy"),
}

_pending: dict[str, dict] = {}
_room = None
_stop_event: Optional[asyncio.Event] = None
_poll_task: Optional[asyncio.Task] = None
_bot_info: dict = {}


def _token() -> str:
    import config as cfg
    return (os.environ.get("TELEGRAM_BOT_TOKEN") or cfg.config.get("telegram_bot_token") or "").strip()


def _default_chat_id() -> str:
    import config as cfg
    return (os.environ.get("TELEGRAM_CHAT_ID") or cfg.config.get("telegram_chat_id") or "").strip()


def _load_chats() -> list:
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _save_chats(chats: list):
    os.makedirs(os.path.dirname(CHATS_FILE), exist_ok=True)
    with open(CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(chats[-50:], f, indent=2, ensure_ascii=False)


def _register_chat(chat_id: str, username: str = "", first_name: str = ""):
    chats = _load_chats()
    cid = str(chat_id)
    if not any(c.get("chat_id") == cid for c in chats):
        chats.append({
            "chat_id": cid,
            "username": username,
            "first_name": first_name,
            "registered_at": __import__("datetime").datetime.now().isoformat(),
        })
        _save_chats(chats)
    if not _default_chat_id():
        _persist_default_chat_id(cid)


def _persist_default_chat_id(chat_id: str):
    import config as cfg
    cfg.config["telegram_chat_id"] = str(chat_id)
    cfg_file = os.path.join(os.path.dirname(__file__), "..", "config.json")
    try:
        with open(cfg_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["telegram_chat_id"] = str(chat_id)
        data["telegram_notify_tasks"] = True
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        cfg.config["telegram_notify_tasks"] = True
    except Exception:
        pass


def _is_allowed(chat_id: str) -> bool:
    cid = str(chat_id)
    if cid == _default_chat_id():
        return True
    return any(c.get("chat_id") == cid for c in _load_chats())


async def _api(method: str, **kwargs) -> dict:
    token = _token()
    if not token:
        return {"ok": False, "description": "no token"}
    import httpx
    url = API_BASE.format(token=token, method=method)
    async with httpx.AsyncClient(timeout=35.0) as client:
        r = await client.post(url, json=kwargs)
        try:
            return r.json()
        except Exception:
            return {"ok": False, "description": r.text[:200]}


async def send_message(chat_id: str, text: str, reply_markup: dict = None, parse_mode: str = None) -> dict:
    payload = {"chat_id": str(chat_id), "text": text[:4000]}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if parse_mode:
        payload["parse_mode"] = parse_mode
    return await _api("sendMessage", **payload)


def main_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Статус", "callback_data": "cmd:status"},
                {"text": "📋 Задачи", "callback_data": "cmd:tasks"},
            ],
            [
                {"text": "🏃 Standup", "callback_data": "cmd:standup"},
                {"text": "👥 Агенты", "callback_data": "cmd:agents"},
            ],
            [
                {"text": "🌐 Landing", "callback_data": "task:landing"},
                {"text": "⚙️ REST API", "callback_data": "task:api"},
            ],
            [
                {"text": "🎨 UI форма", "callback_data": "task:ui"},
                {"text": "🧪 Тесты", "callback_data": "task:tests"},
            ],
            [
                {"text": "📽️ Pitch", "callback_data": "task:pitch"},
                {"text": "🧊 3D Hero", "callback_data": "task:3d"},
            ],
            [
                {"text": "🚀 Deploy", "callback_data": "cmd:deploy"},
                {"text": "📤 Git Sync", "callback_data": "cmd:sync"},
            ],
            [
                {"text": "💬 Своя задача", "callback_data": "mode:task"},
                {"text": "📌 Меню", "callback_data": "cmd:menu"},
            ],
        ]
    }


def target_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "👥 Вся команда", "callback_data": "target:all"},
                {"text": "👔 PM", "callback_data": "target:pm"},
            ],
            [
                {"text": "🎨 Соня", "callback_data": "target:frontend"},
                {"text": "⚡ Лео", "callback_data": "target:cursor"},
            ],
            [
                {"text": "⚙️ Backend", "callback_data": "target:backend"},
                {"text": "🧪 QA", "callback_data": "target:qa"},
            ],
            [{"text": "← Меню", "callback_data": "cmd:menu"}],
        ]
    }


async def _answer_callback(callback_id: str, text: str = ""):
    await _api("answerCallbackQuery", callback_query_id=callback_id, text=text[:200])


async def _edit_or_send(chat_id: str, message_id: int, text: str, markup: dict = None):
    r = await _api(
        "editMessageText",
        chat_id=str(chat_id),
        message_id=message_id,
        text=text[:4000],
        reply_markup=markup or main_keyboard(),
    )
    if not r.get("ok"):
        await send_message(chat_id, text, reply_markup=markup or main_keyboard())


def _format_status(room) -> str:
    stats = room.task_history.stats()
    working = [a for a in room.agents.values() if a.status in ("working", "learning", "thinking")]
    lines = [
        "📊 *Статус AI Team Room*",
        "",
        f"Задач: ✅ {stats.get('completed', 0)} · ⚡ {stats.get('active', 0)} · 📦 {stats.get('total', 0)}",
    ]
    if working:
        lines.append("Активны: " + ", ".join(f"{a.emoji}{a.name}" for a in working[:6]))
    else:
        lines.append("Команда в ожидании — можно давать задачи.")
    lines.append(f"\n🌐 Dashboard: {_app_url()}/app?view=dashboard")
    return "\n".join(lines)


def _format_tasks(room, limit: int = 8) -> str:
    tasks = room.task_history.get_all()[:limit]
    if not tasks:
        return "📋 Задач пока нет.\n\nИспользуйте кнопки ниже или напишите задачу текстом."
    lines = ["📋 *Последние задачи*", ""]
    status_emoji = {
        "completed": "✅", "in_progress": "⚡", "failed": "❌",
        "submitted": "📥", "queued": "⏳",
    }
    for t in tasks:
        st = status_emoji.get(t.get("status"), "•")
        agent = t.get("agent_name") or t.get("target") or "—"
        text = (t.get("task") or "")[:55]
        lines.append(f"{st} *{agent}*: {text}")
    return "\n".join(lines)


def _format_agents(room) -> str:
    lines = ["👥 *Команда агентов*", ""]
    for a in room.agents.values():
        state = a.get_state()
        count = state.get("artifact_count", 0)
        lines.append(f"{a.emoji} *{a.name}* — `{a.status}` · артефактов: {count}")
    return "\n".join(lines)


def _app_url() -> str:
    import config as cfg
    port = cfg.config.get("port", 8000)
    return os.environ.get("APP_PUBLIC_URL") or f"http://localhost:{port}"


async def _submit_task(room, text: str, target: str = "all", source: str = "Telegram"):
    await room.handle_user_message({
        "type": "task",
        "text": f"[{source}] {text}" if not text.startswith("[") else text,
        "target": target,
    })


async def _handle_command(chat_id: str, cmd: str, room, message_id: int = None):
    if cmd == "menu":
        text = "🤖 *AI Team Room*\n\nВыберите действие или напишите задачу текстом:"
        if message_id:
            await _edit_or_send(chat_id, message_id, text, main_keyboard())
        else:
            await send_message(chat_id, text, reply_markup=main_keyboard(), parse_mode="Markdown")
        return

    if cmd == "status":
        text = _format_status(room)
    elif cmd == "tasks":
        text = _format_tasks(room)
    elif cmd == "agents":
        text = _format_agents(room)
    elif cmd == "standup":
        from integrations.standup import generate_standup
        standup = generate_standup(room)
        text = standup.get("narrative", "Standup недоступен")
    elif cmd == "deploy":
        try:
            from integrations.deploy_export import create_deploy_bundle
            info = create_deploy_bundle()
            text = f"🚀 Deploy ZIP готов\n{_app_url()}/api/deploy/download\n\n{info.get('message', '')}"
        except Exception as e:
            text = f"❌ Deploy: {e}"
    elif cmd == "sync":
        try:
            from integrations.local_git_sync import sync_changes_async
            result = await sync_changes_async("telegram: manual sync")
            action = result.get("action", "none")
            text = f"📤 Git Sync: {action}"
            if result.get("commit"):
                text += f"\nCommit: `{result.get('commit')}`"
        except Exception as e:
            text = f"❌ Sync: {e}"
    else:
        text = "Неизвестная команда"

    markup = main_keyboard()
    if message_id:
        await _edit_or_send(chat_id, message_id, text, markup)
    else:
        await send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")


async def handle_update(update: dict, room):
    global _room
    _room = room

    if update.get("callback_query"):
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb.get("data", "")
        if not _is_allowed(chat_id):
            await _answer_callback(cb["id"], "Чат не авторизован. Отправьте /start")
            return
        await _answer_callback(cb["id"])

        if data.startswith("cmd:"):
            await _handle_command(chat_id, data.split(":", 1)[1], room, msg_id)
        elif data.startswith("task:"):
            key = data.split(":", 1)[1]
            tpl = QUICK_TASKS.get(key)
            if tpl:
                target, text = tpl
                await _submit_task(room, text, target)
                await _edit_or_send(chat_id, msg_id, f"✅ Задача отправлена → *{target}*\n\n_{text[:120]}_", main_keyboard())
        elif data.startswith("mode:"):
            mode = data.split(":", 1)[1]
            if mode == "task":
                _pending[str(chat_id)] = {"mode": "task", "target": "all"}
                await send_message(
                    chat_id,
                    "💬 Напишите задачу следующим сообщением.\nИли выберите кому отправить:",
                    reply_markup=target_keyboard(),
                )
        elif data.startswith("target:"):
            target = data.split(":", 1)[1]
            pending = _pending.get(str(chat_id), {})
            if pending.get("mode") == "task":
                _pending[str(chat_id)] = {"mode": "task", "target": target}
                await send_message(chat_id, f"✏️ Пишите задачу для `{target}`:", parse_mode="Markdown")
            else:
                _pending[str(chat_id)] = {"mode": "task", "target": target}
                await send_message(chat_id, f"✏️ Режим задачи → `{target}`. Напишите текст:", parse_mode="Markdown")
        return

    message = update.get("message") or update.get("edited_message") or {}
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    user = message.get("from", {})

    if text.startswith("/start"):
        _register_chat(chat_id, user.get("username", ""), user.get("first_name", ""))
        name = user.get("first_name") or "друг"
        await send_message(
            chat_id,
            f"👋 Привет, {name}!\n\n"
            "Вы управляете *AI Team Room* — командой из 11 ИИ-агентов.\n\n"
            "• Кнопки ниже — быстрые задачи и статус\n"
            "• Текстом — любая задача\n"
            "• /menu — показать меню\n"
            "• /help — справка",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )
        return

    if not _is_allowed(chat_id):
        _register_chat(chat_id, user.get("username", ""), user.get("first_name", ""))

    if text.startswith("/help"):
        await send_message(
            chat_id,
            "*Команды:*\n/start — меню\n/status — статус\n/tasks — задачи\n/standup — standup\n/menu — кнопки\n\n"
            "Или просто напишите задачу — она уйдёт всей команде через PM.",
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )
        return

    if text.startswith("/menu"):
        await _handle_command(chat_id, "menu", room)
        return

    if text.startswith("/status"):
        await _handle_command(chat_id, "status", room)
        return

    if text.startswith("/tasks"):
        await _handle_command(chat_id, "tasks", room)
        return

    if text.startswith("/standup"):
        await _handle_command(chat_id, "standup", room)
        return

    if not text or text.startswith("/"):
        return

    pending = _pending.pop(str(chat_id), {})
    target = pending.get("target", "all")
    await _submit_task(room, text, target)
    await send_message(
        chat_id,
        f"✅ Задача принята → `{target}`\n\n_{text[:200]}_",
        reply_markup=main_keyboard(),
        parse_mode="Markdown",
    )


async def polling_loop(room, stop_event: asyncio.Event):
    token = _token()
    if not token:
        return
    me = await _api("getMe")
    if me.get("ok"):
        global _bot_info
        _bot_info = me.get("result", {})
        username = _bot_info.get("username", "?")
        print(f"📱 Telegram Bot: @{username} (polling)")
    else:
        print(f"⚠️ Telegram Bot: {me.get('description', 'invalid token')}")
        return

    offset = 0
    while not stop_event.is_set():
        try:
            data = await _api("getUpdates", offset=offset, timeout=25, allowed_updates=["message", "callback_query", "edited_message"])
            if not data.get("ok"):
                await asyncio.sleep(3)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                try:
                    await handle_update(upd, room)
                except Exception as e:
                    print(f"Telegram update error: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Telegram polling: {e}")
            await asyncio.sleep(5)


async def start_bot(room):
    global _poll_task, _stop_event, _room
    _room = room
    if not _token():
        return
    use_polling = os.environ.get("TELEGRAM_POLLING", "true").lower() not in ("0", "false", "no")
    if not use_polling:
        print("📱 Telegram Bot: webhook mode (/api/telegram/webhook)")
        me = await _api("getMe")
        if me.get("ok"):
            _bot_info.update(me.get("result", {}))
            print(f"   @{_bot_info.get('username', '?')}")
        return
    _stop_event = asyncio.Event()
    _poll_task = asyncio.create_task(polling_loop(room, _stop_event))


async def stop_bot():
    global _poll_task, _stop_event
    if _stop_event:
        _stop_event.set()
    if _poll_task:
        _poll_task.cancel()
        try:
            await _poll_task
        except asyncio.CancelledError:
            pass
        _poll_task = None


def bot_status() -> dict:
    chats = _load_chats()
    return {
        "configured": bool(_token()),
        "polling": os.environ.get("TELEGRAM_POLLING", "true").lower() not in ("0", "false", "no"),
        "username": _bot_info.get("username"),
        "chat_id": _default_chat_id() or (chats[0]["chat_id"] if chats else ""),
        "authorized_chats": len(chats),
        "notify_tasks": __import__("config").config.get("telegram_notify_tasks", False),
    }


async def notify_task(text: str, chat_id: str = None) -> Optional[dict]:
    cid = chat_id or _default_chat_id()
    if not cid:
        chats = _load_chats()
        cid = chats[0]["chat_id"] if chats else ""
    if not cid:
        return None
    return await send_message(cid, text, parse_mode="Markdown")
