"""Telegram Bot — polling, кнопки управления командой."""

import asyncio
import html
import json
import os
import re
from typing import Optional

CHATS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "telegram_chats.json")
OFFSET_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "telegram_offset.json")
API_BASE = "https://api.telegram.org/bot{token}/{method}"

QUICK_TASKS = {
    "landing": ("frontend", "Сделай landing page для стартапа с hero, features и CTA"),
    "api": ("backend", "Напиши REST API для задач на FastAPI"),
    "ui": ("frontend", "Создай форму регистрации в React"),
    "tests": ("qa", "Напиши smoke-тесты для основных API endpoints"),
    "pitch": ("presenter", "Создай pitch deck на 8 слайдов для стартапа"),
    "3d": ("modeler", "Создай интерактивную 3D hero-сцену для продукта"),
}

# Текст кнопок постоянной клавиатуры → действие
REPLY_BUTTONS = {
    "📊 Статус": "cmd:status",
    "📋 Задачи": "cmd:tasks",
    "🏃 Standup": "cmd:standup",
    "👥 Агенты": "cmd:agents",
    "🌐 Landing": "task:landing",
    "⚙️ REST API": "task:api",
    "🎨 UI форма": "task:ui",
    "🧪 Тесты": "task:tests",
    "📽️ Pitch": "task:pitch",
    "🧊 3D Hero": "task:3d",
    "🚀 Deploy": "cmd:deploy",
    "📤 Git Sync": "cmd:sync",
    "✨ Studio": "cmd:studio",
    "💬 Своя задача": "mode:task",
    "📌 Меню": "cmd:menu",
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


def _load_offset() -> int:
    if os.path.exists(OFFSET_FILE):
        try:
            with open(OFFSET_FILE, "r", encoding="utf-8") as f:
                return int(json.load(f).get("offset", 0))
        except Exception:
            pass
    return 0


def _save_offset(offset: int):
    os.makedirs(os.path.dirname(OFFSET_FILE), exist_ok=True)
    with open(OFFSET_FILE, "w", encoding="utf-8") as f:
        json.dump({"offset": offset}, f)


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


def _esc(text: str) -> str:
    return html.escape(str(text or ""), quote=False)


def _md_to_html(text: str) -> str:
    """Конвертирует **bold** и *bold* в HTML для Telegram."""
    t = _esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*(.+?)\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


async def _api(method: str, **kwargs) -> dict:
    token = _token()
    if not token:
        return {"ok": False, "description": "no token"}
    import httpx
    url = API_BASE.format(token=token, method=method)
    try:
        async with httpx.AsyncClient(timeout=35.0, trust_env=False) as client:
            r = await client.post(url, json=kwargs)
            try:
                return r.json()
            except Exception:
                return {"ok": False, "description": r.text[:200]}
    except Exception as e:
        _log(f"API {method} error: {e}")
        return {"ok": False, "description": str(e)}


def _log(msg: str):
    line = f"[telegram] {msg}"
    print(line)
    try:
        log_path = os.path.join(os.path.dirname(__file__), "..", "data", "telegram_bot.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def main_reply_keyboard() -> dict:
    """Постоянная клавиатура внизу экрана — всегда видна."""
    return {
        "keyboard": [
            [{"text": "📊 Статус"}, {"text": "📋 Задачи"}],
            [{"text": "🏃 Standup"}, {"text": "👥 Агенты"}],
            [{"text": "🌐 Landing"}, {"text": "⚙️ REST API"}],
            [{"text": "🎨 UI форма"}, {"text": "🧪 Тесты"}],
            [{"text": "📽️ Pitch"}, {"text": "🧊 3D Hero"}],
            [{"text": "🚀 Deploy"}, {"text": "📤 Git Sync"}],
            [{"text": "✨ Studio"}, {"text": "💬 Своя задача"}],
            [{"text": "📌 Меню"}],
        ],
        "resize_keyboard": True,
        "is_persistent": True,
    }


def main_inline_keyboard() -> dict:
    """Inline-кнопки под сообщением."""
    return {
        "inline_keyboard": [
            [
                {"text": "📊 Статус", "callback_data": "cmd:status"},
                {"text": "📋 Задачи", "callback_data": "cmd:tasks"},
            ],
            [
                {"text": "🌐 Landing", "callback_data": "task:landing"},
                {"text": "⚙️ REST API", "callback_data": "task:api"},
            ],
            [
                {"text": "💬 Своя задача", "callback_data": "mode:task"},
                {"text": "✨ Studio", "callback_data": "cmd:studio"},
            ],
            [
                {"text": "📌 Обновить меню", "callback_data": "cmd:menu"},
            ],
        ]
    }


def target_inline_keyboard() -> dict:
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
            [{"text": "← Меню", "callback_data": "cmd:menu"}],
        ]
    }


async def send_message(
    chat_id: str,
    text: str,
    reply_markup: dict = None,
    parse_mode: str = None,
    html_text: str = None,
) -> dict:
    """Отправка с fallback — клавиатура сохраняется при ошибке форматирования."""
    markup = reply_markup or main_reply_keyboard()
    tries = []
    if html_text is not None:
        tries.append((html_text, "HTML"))
    elif parse_mode:
        tries.append((text, parse_mode))
    tries.append((text, None))

    last = {"ok": False}
    for body, mode in tries:
        payload = {"chat_id": str(chat_id), "text": body[:4000], "reply_markup": markup}
        if mode:
            payload["parse_mode"] = mode
        last = await _api("sendMessage", **payload)
        if last.get("ok"):
            return last
    print(f"Telegram sendMessage failed: {last.get('description', last)}")
    return last


async def _answer_callback(callback_id: str, text: str = ""):
    await _api("answerCallbackQuery", callback_query_id=callback_id, text=text[:200])


async def _edit_or_send(chat_id: str, message_id: int, text: str, html_body: str = None, inline_markup: dict = None):
    body = html_body if html_body is not None else _md_to_html(text)
    markup = inline_markup or main_inline_keyboard()
    r = await _api(
        "editMessageText",
        chat_id=str(chat_id),
        message_id=message_id,
        text=body[:4000],
        parse_mode="HTML",
        reply_markup=markup,
    )
    if not r.get("ok"):
        await send_message(chat_id, text, reply_markup=main_reply_keyboard())


def _format_status(room) -> tuple[str, str]:
    stats = room.task_history.stats()
    working = [a for a in room.agents.values() if a.status in ("working", "learning", "thinking")]
    plain = [
        "📊 Статус AI Team Room",
        "",
        f"Задач: ✅ {stats.get('completed', 0)} · ⚡ {stats.get('active', 0)} · 📦 {stats.get('total', 0)}",
    ]
    if working:
        plain.append("Активны: " + ", ".join(f"{a.emoji}{a.name}" for a in working[:6]))
    else:
        plain.append("Команда в ожидании — можно давать задачи.")
    plain.append(f"\nDashboard: {_app_url()}/workspace?view=dashboard")
    text = "\n".join(plain)
    return text, _md_to_html(text.replace("📊 Статус", "<b>📊 Статус AI Team Room</b>", 1))


def _format_tasks(room, limit: int = 8) -> tuple[str, str]:
    tasks = room.task_history.get_all()[:limit]
    if not tasks:
        text = "📋 Задач пока нет.\n\nНажмите кнопку внизу или напишите задачу текстом."
        return text, _esc(text)
    lines = ["📋 Последние задачи", ""]
    status_emoji = {"completed": "✅", "in_progress": "⚡", "failed": "❌", "submitted": "📥", "queued": "⏳"}
    html_lines = ["<b>📋 Последние задачи</b>", ""]
    for t in tasks:
        st = status_emoji.get(t.get("status"), "•")
        agent = t.get("agent_name") or t.get("target") or "—"
        task_text = (t.get("task") or "")[:55]
        lines.append(f"{st} {agent}: {task_text}")
        html_lines.append(f"{st} <b>{_esc(agent)}</b>: {_esc(task_text)}")
    return "\n".join(lines), "\n".join(html_lines)


def _format_agents(room) -> tuple[str, str]:
    lines = ["👥 Команда агентов", ""]
    html_lines = ["<b>👥 Команда агентов</b>", ""]
    for a in room.agents.values():
        state = a.get_state()
        count = state.get("artifact_count", 0)
        lines.append(f"{a.emoji} {a.name} — {a.status} · артефактов: {count}")
        html_lines.append(f"{a.emoji} <b>{_esc(a.name)}</b> — <code>{_esc(a.status)}</code> · {_esc(str(count))}")
    return "\n".join(lines), "\n".join(html_lines)


def _app_url() -> str:
    import config as cfg
    port = cfg.config.get("port", 8000)
    return os.environ.get("APP_PUBLIC_URL") or f"http://localhost:{port}"


async def _typing(chat_id: str):
    await _api("sendChatAction", chat_id=str(chat_id), action="typing")


def _match_reply_button(text: str) -> Optional[str]:
    text = (text or "").strip()
    if text in REPLY_BUTTONS:
        return REPLY_BUTTONS[text]
    for label, action in REPLY_BUTTONS.items():
        if label.replace(" ", "") == text.replace(" ", ""):
            return action
    return None


def _submit_task_background(room, text: str, target: str = "all", source: str = "Telegram"):
    """Задача в фоне — не блокирует polling и другие кнопки."""
    payload = {
        "type": "task",
        "text": f"[{source}] {text}" if not text.startswith("[") else text,
        "target": target,
    }

    async def _run():
        try:
            await room.handle_user_message(payload)
        except Exception as e:
            print(f"Telegram task error: {e}")

    asyncio.create_task(_run())


async def _run_action(chat_id: str, action: str, room, message_id: int = None):
    """Выполняет cmd:* / task:* / mode:*."""
    await _typing(chat_id)
    try:
        if action.startswith("cmd:"):
            await _handle_command(chat_id, action.split(":", 1)[1], room, message_id)
        elif action.startswith("task:"):
            key = action.split(":", 1)[1]
            tpl = QUICK_TASKS.get(key)
            if tpl:
                target, task_text = tpl
                msg = f"✅ Задача принята → {target}\n\n{task_text[:120]}\n\n⏳ Команда работает…"
                if message_id:
                    await _edit_or_send(chat_id, message_id, msg)
                else:
                    await send_message(chat_id, msg, reply_markup=main_reply_keyboard())
                _submit_task_background(room, task_text, target)
        elif action.startswith("mode:"):
            if action.split(":", 1)[1] == "task":
                _pending[str(chat_id)] = {"mode": "task", "target": "all"}
                await send_message(
                    chat_id,
                    "💬 Напишите задачу следующим сообщением.\nИли выберите агента:",
                    reply_markup=main_reply_keyboard(),
                )
                await send_message(
                    chat_id,
                    "Кому отправить?",
                    reply_markup=target_inline_keyboard(),
                )
        elif action.startswith("target:"):
            target = action.split(":", 1)[1]
            _pending[str(chat_id)] = {"mode": "task", "target": target}
            await send_message(
                chat_id,
                f"✏️ Напишите задачу для: {target}",
                reply_markup=main_reply_keyboard(),
            )
    except Exception as e:
        print(f"Telegram action error [{action}]: {e}")
        await send_message(chat_id, f"❌ Ошибка: {e}", reply_markup=main_reply_keyboard())


def _format_studio() -> tuple[str, str]:
    from integrations.sonya_studio import list_projects

    base = f"{_app_url()}/workspace?view=sonya-studio"
    projects = list_projects()[:8]
    if not projects:
        text = f"✨ Sonya Design Studio\n\nПроектов пока нет.\nОткройте Studio в браузере:\n{base}"
        return text, _esc(text)

    lines = ["✨ **Sonya Design Studio**", "", "Последние проекты:"]
    for p in projects:
        st = {"draft": "черновик", "review": "ревью", "published": "опубликован"}.get(p.get("status"), p.get("status"))
        oc = f" · 💬 {p['open_comments']}" if p.get("open_comments") else ""
        lines.append(f"• «{p.get('title')}» — {st}, v{p.get('version_count', 1)}{oc}")
    lines.append("")
    lines.append(f"→ {base}")
    text = "\n".join(lines)
    return text, _md_to_html(text)


async def _handle_command(chat_id: str, cmd: str, room, message_id: int = None):
    html_body = None
    if cmd == "menu":
        text = "🤖 AI Team Room\n\nИспользуйте кнопки внизу экрана или inline-кнопки ниже."
        html_body = "<b>🤖 AI Team Room</b>\n\nИспользуйте кнопки внизу экрана 👇"
        if message_id:
            await _edit_or_send(chat_id, message_id, text, html_body, main_inline_keyboard())
        else:
            await send_message(chat_id, text, reply_markup=main_reply_keyboard(), html_text=html_body)
            await send_message(chat_id, "Быстрые действия:", reply_markup=main_inline_keyboard())
        return

    if cmd == "status":
        text, html_body = _format_status(room)
    elif cmd == "tasks":
        text, html_body = _format_tasks(room)
    elif cmd == "agents":
        text, html_body = _format_agents(room)
    elif cmd == "standup":
        from integrations.standup import generate_standup
        standup = generate_standup(room)
        text = standup.get("narrative", "Standup недоступен")
        html_body = _md_to_html(text)
    elif cmd == "deploy":
        try:
            from integrations.deploy_export import create_deploy_bundle
            info = create_deploy_bundle()
            text = f"🚀 Deploy ZIP готов\n{_app_url()}/api/deploy/download"
        except Exception as e:
            text = f"❌ Deploy: {e}"
        html_body = _esc(text)
    elif cmd == "studio":
        text, html_body = _format_studio()
    elif cmd == "sync":
        text = "📤 Git Sync запущен…"
        html_body = _esc(text)

        async def _do_sync():
            try:
                from integrations.local_git_sync import sync_changes_async
                result = await sync_changes_async("telegram: manual sync")
                sync_text = f"📤 Git Sync: {result.get('action', 'none')}"
                if result.get("commit"):
                    sync_text += f"\nCommit: {result.get('commit')}"
                await send_message(chat_id, sync_text, reply_markup=main_reply_keyboard())
            except Exception as e:
                await send_message(chat_id, f"❌ Sync: {e}", reply_markup=main_reply_keyboard())

        asyncio.create_task(_do_sync())
    else:
        text = "Неизвестная команда"
        html_body = _esc(text)

    if message_id:
        await _edit_or_send(chat_id, message_id, text, html_body, main_inline_keyboard())
    else:
        await send_message(chat_id, text, reply_markup=main_reply_keyboard(), html_text=html_body)


async def _safe_handle_update(update: dict, room):
    global _room
    _room = room
    msg = update.get("message") or update.get("edited_message") or {}
    cb = update.get("callback_query", {})
    chat_id = (msg.get("chat") or cb.get("message", {}).get("chat") or {}).get("id")
    try:
        await _handle_update_inner(update, room)
    except Exception as e:
        print(f"Telegram handle_update error: {e}")
        if chat_id:
            try:
                await send_message(chat_id, f"❌ Ошибка бота: {e}", reply_markup=main_reply_keyboard())
            except Exception:
                pass


async def _handle_update_inner(update: dict, room):
    if update.get("callback_query"):
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        msg_id = cb["message"]["message_id"]
        data = cb.get("data", "")
        _log(f"callback chat={chat_id} data={data!r}")
        if not _is_allowed(chat_id):
            _register_chat(chat_id, cb.get("from", {}).get("username", ""), cb.get("from", {}).get("first_name", ""))
        await _answer_callback(cb["id"], "⏳")
        await _run_action(chat_id, data, room, msg_id)
        return

    message = update.get("message") or update.get("edited_message") or {}
    if not message:
        return

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip()
    user = message.get("from", {})
    _log(f"msg chat={chat_id} text={text!r}")

    if text.startswith("/ping"):
        await send_message(chat_id, "🏓 pong — бот работает", reply_markup=main_reply_keyboard())
        return

    if text.startswith("/start"):
        _register_chat(chat_id, user.get("username", ""), user.get("first_name", ""))
        name = _esc(user.get("first_name") or "друг")
        html_body = (
            f"👋 Привет, {name}!\n\n"
            "<b>AI Team Room</b> — команда из 11 ИИ-агентов.\n\n"
            "Кнопки управления — <b>внизу экрана</b> 👇\n"
            "• Текстом — любая задача\n"
            "• /menu — обновить меню"
        )
        await send_message(
            chat_id,
            "Привет! Кнопки управления — внизу экрана.",
            reply_markup=main_reply_keyboard(),
            html_text=html_body,
        )
        await send_message(chat_id, "Быстрые inline-кнопки:", reply_markup=main_inline_keyboard())
        return

    if not _is_allowed(chat_id):
        _register_chat(chat_id, user.get("username", ""), user.get("first_name", ""))

    action = _match_reply_button(text)
    if action:
        print(f"Telegram button: {text!r} -> {action}")
        await _run_action(chat_id, action, room)
        return

    if text.startswith("/help"):
        await send_message(
            chat_id,
            "Команды: /start /menu /status /tasks /standup /studio\nИли кнопки внизу экрана.",
            reply_markup=main_reply_keyboard(),
        )
        return

    for cmd in ("menu", "status", "tasks", "standup", "studio"):
        if text.startswith(f"/{cmd}"):
            await _handle_command(chat_id, cmd, room)
            return

    if not text or text.startswith("/"):
        return

    pending = _pending.pop(str(chat_id), {})
    target = pending.get("target", "all")
    await send_message(
        chat_id,
        f"✅ Задача принята → {target}\n\n{text[:200]}\n\n⏳ Команда работает…",
        reply_markup=main_reply_keyboard(),
    )
    _submit_task_background(room, text, target)


async def handle_update(update: dict, room):
    await _safe_handle_update(update, room)


async def _prepare_bot():
    """Сброс webhook (иначе polling не работает) + команды бота."""
    await _api("deleteWebhook", drop_pending_updates=False)
    await _api(
        "setMyCommands",
        commands=[
            {"command": "start", "description": "Меню и кнопки"},
            {"command": "menu", "description": "Показать меню"},
            {"command": "status", "description": "Статус команды"},
            {"command": "tasks", "description": "Последние задачи"},
            {"command": "standup", "description": "Standup-сводка"},
            {"command": "help", "description": "Справка"},
        ],
    )


async def polling_loop(room, stop_event: asyncio.Event):
    token = _token()
    if not token:
        return

    await _prepare_bot()

    offset = _load_offset()
    _log(f"polling offset={offset}")
    while not stop_event.is_set():
        try:
            data = await _api(
                "getUpdates",
                offset=offset,
                timeout=25,
                allowed_updates=["message", "callback_query", "edited_message"],
            )
            if not data.get("ok"):
                await asyncio.sleep(3)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                _save_offset(offset)
                try:
                    await _safe_handle_update(upd, room)
                except Exception as e:
                    _log(f"update error: {e}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Telegram polling: {e}")
            await asyncio.sleep(5)


async def start_bot(room):
    global _poll_task, _stop_event, _room, _bot_info
    _room = room
    if not _token():
        _log("TELEGRAM_BOT_TOKEN not set")
        return
    if os.environ.get("TELEGRAM_EMBEDDED", "true").lower() in ("0", "false", "no"):
        _log("embedded polling disabled (use telegram_standalone.py)")
        return
    use_polling = os.environ.get("TELEGRAM_POLLING", "true").lower() not in ("0", "false", "no")
    await _prepare_bot()
    me = await _api("getMe")
    if not me.get("ok"):
        _log(f"getMe failed: {me.get('description', me)}")
        return
    _bot_info = me.get("result", {})
    username = _bot_info.get("username", "?")
    if not use_polling:
        _log(f"webhook mode @{username}")
        return
    _log(f"started @{username} polling, chat_id={_default_chat_id() or 'auto on /start'}")
    _stop_event = asyncio.Event()
    _poll_task = asyncio.create_task(polling_loop(room, _stop_event))

    def _on_poll_done(t: asyncio.Task):
        try:
            exc = t.exception()
            if exc:
                _log(f"polling crashed: {exc}")
        except Exception:
            pass

    _poll_task.add_done_callback(_on_poll_done)


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
        "notify_studio": __import__("config").config.get("telegram_notify_studio", True),
        "reply_keyboard": True,
    }


async def notify_task(text: str, chat_id: str = None) -> Optional[dict]:
    cid = chat_id or _default_chat_id()
    if not cid:
        chats = _load_chats()
        cid = chats[0]["chat_id"] if chats else ""
    if not cid:
        return None
    return await send_message(cid, text, reply_markup=main_reply_keyboard(), html_text=_md_to_html(text))


# backwards compat
main_keyboard = main_inline_keyboard
