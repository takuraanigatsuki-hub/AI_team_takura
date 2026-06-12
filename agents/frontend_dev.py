from datetime import datetime
from typing import Optional

from agents.base_agent import BaseAgent
from agents.react_preview import generate_react_preview, is_site_task, apply_figma_tokens
from room.task_routing import should_emit_react_preview, should_export_site, classify_task_kind
from site_exporter import export_site_html
from integrations.figma_client import parse_figma_url, get_client_async


class FrontendDevAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="frontend",
            name="Соня",
            role="Frontend Developer",
            emoji="🎨",
            description=(
                "Ты senior frontend разработчик. Мастер React, TypeScript, CSS. "
                "Помешана на UX и доступности. Создаёшь красивые, быстрые и "
                "интуитивные интерфейсы. Следишь за Core Web Vitals, "
                "любишь анимации и микровзаимодействия."
            ),
            room_manager=room_manager
        )
        self.last_preview = None
        self.last_figma = None
        self.figma_studies = 0
        self.figma_creations = 0

    async def _learn(self):
        if not self.task_queue.empty():
            return
        # Figma Studio — отдельный фоновый цикл sonya_figma_studio_loop (без дублирования API)
        await super()._learn()

    async def apply_figma_design(self, figma_result: dict):
        """Применить импортированный макет Figma."""
        from integrations.figma_react import generate_react_from_figma

        self.last_figma = figma_result
        summary = figma_result.get("summary", {})
        task_text = f"UI по макету Figma: {summary.get('file_name', 'Design')}"
        colors = summary.get("colors", [])
        color_hint = ", ".join(colors[:5]) if colors else ""
        enhanced = f"{task_text}. Цвета: {color_hint}. Адаптивный React-компонент."

        preview = generate_react_from_figma(figma_result, task=enhanced)
        preview["task"] = enhanced
        preview["timestamp"] = datetime.now().isoformat()
        self.last_preview = preview

        if preview.get("is_site"):
            try:
                site_path = export_site_html(preview["code"], enhanced, preview["title"])
                preview["site_path"] = site_path
                preview["site_url"] = "/api/sites/latest"
            except Exception:
                pass

        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": "react_preview",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "title": preview["title"],
                "code": preview["code"],
                "task": enhanced,
                "timestamp": preview["timestamp"],
                "is_site": preview.get("is_site", False),
                "site_url": preview.get("site_url"),
                "figma_file_key": preview.get("figma_file_key"),
            })
        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": "figma_import",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "title": summary.get("file_name", "Figma"),
                "colors": colors,
                "preview_url": figma_result.get("preview_url"),
                "css_tokens": figma_result.get("css_tokens"),
                "message": f"🎨 Макет «{summary.get('file_name')}» импортирован — React Preview обновлён.",
                "timestamp": datetime.now().isoformat(),
            })

    def _extract_figma_url(self, text: str) -> str:
        for word in text.split():
            if "figma.com" in word:
                return word.strip("()[]<>\"'")
        return ""

    def get_responsibilities(self) -> str:
        return (
            "- Разработка пользовательских интерфейсов\n"
            "- Интеграция с backend API\n"
            "- Оптимизация производительности фронтенда\n"
            "- Обеспечение кросс-браузерной совместимости\n"
            "- Реализация адаптивного дизайна\n"
            "- Работа с состоянием приложения"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🎨 Готово: '{task}'!\n\nКомпонент собран на React — откройте **React Preview** справа, чтобы увидеть результат вживую.",
            "🎨 Задача '{task}' выполнена.\n\nUI отрисован в preview-панели. Использованы хуки, inline-стили и адаптивная вёрстка.",
            "🎨 '{task}' — компонент готов!\n\nНажмите «Preview» или смотрите панель React Preview — там живой рендер.",
        ]

    def _build_preview(self, task_text: str) -> dict:
        preview = generate_react_preview(task_text)
        if self.last_figma:
            preview = apply_figma_tokens(preview, self.last_figma)
        preview["task"] = task_text
        preview["timestamp"] = datetime.now().isoformat()
        self.last_preview = preview
        return preview

    async def _emit_preview(self, task_text: str):
        if not should_emit_react_preview(task_text):
            return
        preview = self._build_preview(task_text)
        if preview.get("is_site") or should_export_site(task_text):
            try:
                site_path = export_site_html(preview["code"], task_text, preview["title"])
                preview["site_path"] = site_path
                preview["site_url"] = "/api/sites/latest"
            except Exception:
                pass

        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": "react_preview",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "title": preview["title"],
                "code": preview["code"],
                "task": task_text,
                "timestamp": preview["timestamp"],
                "is_site": preview.get("is_site", False),
                "site_url": preview.get("site_url"),
            })
            if preview.get("is_site"):
                await self.room_manager.broadcast_work({
                    "type": "site_ready",
                    "agent_name": self.name,
                    "title": preview["title"],
                    "site_url": preview.get("site_url", "/api/sites/latest"),
                    "message": f"🌐 Сайт готов! Откройте React Preview или {preview.get('site_url', '/api/sites/latest')}",
                    "timestamp": preview["timestamp"],
                })

    async def handle_direct_chat(self, text: str, force_chat: bool = False):
        from room.user_intent import classify_user_message, record_user_wish

        self.direct_chat.append({
            "role": "user",
            "text": text,
            "timestamp": datetime.now().isoformat()
        })
        self.status = "working"
        self.location = "studio"

        if self.room_manager:
            await self.room_manager.broadcast({
                "type": "direct_user_echo",
                "agent_id": self.agent_id,
                "message": text,
                "timestamp": datetime.now().isoformat()
            })

        record_user_wish(text, self.agent_id)

        reply = await self._maybe_handle_studio_command(text)
        if reply is not None:
            await self._save_direct_reply(reply)
            return

        if classify_user_message(text, force_chat=force_chat) == "work":
            reply = await self._start_user_task(text, sender="Пользователь")
            await self._save_direct_reply(reply, status="working")
            return

        response = await self._build_response(text)
        if should_emit_react_preview(text):
            await self._emit_preview(text)
            response += f"\n\n🖥️ **React Preview** обновлён — смотрите панель «{self.last_preview['title']}»."
        await self._save_direct_reply(response)

    async def _save_direct_reply(self, reply: str, status: str = "idle"):
        from direct_chat_store import DirectChatStore
        self.direct_chat.append({
            "role": "agent",
            "text": reply,
            "timestamp": datetime.now().isoformat()
        })
        DirectChatStore.save(self.agent_id, self.direct_chat)
        if self.room_manager:
            await self.room_manager.broadcast({
                "type": "direct_agent_message",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": reply,
                "status": status,
                "location": self.location,
                "timestamp": datetime.now().isoformat()
            })
        if status == "idle":
            self.status = "idle"

    async def _process_task(self, task: dict):
        self.status = "working"
        self.location = "studio"
        self.current_task = task
        task_text = task.get("text", "")
        sender = task.get("sender", "Пользователь")
        task_id = task.get("task_id")

        if self.room_manager and task_id:
            self.room_manager.record_task_started(task_id)

        await self._broadcast_work(
            f"📋 Задача от {sender}: *{task_text}*\nВерстаю в React Preview...",
            "task_received"
        )

        if await self._maybe_handle_studio_command(task_text, task_id=task_id, sender=sender) is not None:
            if self.room_manager:
                await self.room_manager._broadcast_task_history()
            self.status = "idle"
            self.current_task = None
            return

        response = ""
        try:
            figma_url = self._extract_figma_url(task_text)
            if figma_url:
                from integrations.figma_client import is_figma_api_url
                from integrations.figma_rate_limit import FigmaRateLimitError

                client = await get_client_async()
                if client.configured and is_figma_api_url(figma_url):
                    try:
                        figma_data = await client.import_design(figma_url)
                        await self.apply_figma_design(figma_data)
                    except FigmaRateLimitError:
                        await self._broadcast_work(
                            "⏳ Figma API временно недоступен — верстаю UI по описанию задачи.",
                            "learning",
                        )
                    except Exception as e:
                        await self._broadcast_work(
                            f"ℹ️ Figma: {e}. Продолжаю по тексту задачи.",
                            "learning",
                        )
                elif figma_url:
                    await self._broadcast_work(
                        "ℹ️ Ссылка Figma Sites/Proto не поддерживается API — верстаю по описанию.",
                        "learning",
                    )

            await self._emit_preview(task_text)

            response = self.build_task_response(task_text, self._find_relevant_knowledge(task_text))
            if self.last_preview and (self.last_preview.get("is_site") or is_site_task(task_text)):
                response += (
                    f"\n\n🌐 **Сайт готов!**\n"
                    f"• Нажмите **🎨 Preview** в шапке — живой просмотр\n"
                    f"• Или откройте в браузере: /api/sites/latest"
                )
            elif self.last_preview and classify_task_kind(task_text) == "table":
                response += (
                    f"\n\n📊 **Таблица готова** — откройте **React Preview** «{self.last_preview['title']}» "
                    "(не landing, интерактивная таблица)."
                )
            elif self.last_preview:
                response += f"\n\n🖥️ Откройте **React Preview** — «{self.last_preview['title']}»"

            await self._broadcast_work(f"✅ Выполнено:\n{response}", "task_done")
            if self.room_manager and task_id:
                self.room_manager.record_task_completed(
                    task_id, response, self.name, self.emoji
                )
        except Exception as e:
            err = str(e)
            await self._broadcast_work(f"❌ Ошибка: {err}", "error")
            if self.room_manager and task_id:
                self.room_manager.record_task_failed(task_id, err)
        finally:
            if self.room_manager:
                await self.room_manager._broadcast_task_history()
            self.memory.append({
                "task": task_text,
                "response": response,
                "preview_title": self.last_preview["title"] if self.last_preview else None,
                "timestamp": datetime.now().isoformat()
            })
            self.status = "idle"
            self.current_task = None

    def get_state(self) -> dict:
        state = super().get_state()
        state["has_preview"] = self.last_preview is not None
        state["preview_title"] = self.last_preview.get("title") if self.last_preview else None
        state["has_figma"] = self.last_figma is not None
        state["figma_studies"] = self.figma_studies
        state["figma_creations"] = self.figma_creations
        try:
            from integrations.figma_learning import get_studio_stats
            stats = get_studio_stats()
            state["figma_portfolio_count"] = stats.get("portfolio_count", 0)
            state["figma_studied_count"] = stats.get("studied_count", 0)
        except Exception:
            pass
        return state

    async def _maybe_handle_studio_command(
        self,
        text: str,
        *,
        task_id: str = None,
        sender: str = "Пользователь",
    ) -> Optional[str]:
        from integrations.sonya_commands import match_studio_intent
        from integrations.sonya_studio import (
            create_studio_project,
            list_projects,
            apply_open_comments,
            publish_project,
        )

        intent = match_studio_intent(text)
        if not intent:
            return None

        action = intent["action"]

        if action == "open_studio":
            msg = "✨ Откройте вкладку **Studio** в приложении — там проекты, комментарии и публикация."
            await self._broadcast_work(msg, "message")
            if self.room_manager:
                await self.room_manager.broadcast_work({
                    "type": "sonya_studio_hint",
                    "agent_id": self.agent_id,
                    "message": msg,
                    "open_view": "sonya-studio",
                    "timestamp": datetime.now().isoformat(),
                })
            return msg

        if action == "create":
            title = intent.get("title") or ""
            task = intent.get("task") or text
            project = await create_studio_project(self, title=title, task=task)
            response = (
                f"✨ **Sonya Studio** · проект «{project.get('title')}» создан!\n"
                f"Откройте вкладку **Studio** — можно оставлять комментарии на макете."
            )
            await self._broadcast_work(response, "task_done")
            if self.room_manager and task_id:
                self.room_manager.record_task_completed(task_id, response, self.name, self.emoji)
            return response

        projects = list_projects()
        if not projects:
            msg = "📭 В Studio пока нет проектов. Скажите «создай новый проект» или нажмите 🎨 Соня."
            await self._broadcast_work(msg, "message")
            return msg

        pid = projects[0]["id"]

        if action == "apply_comments":
            try:
                updated = await apply_open_comments(self, pid)
                response = (
                    f"🔧 Правки применены · «{updated.get('title')}» "
                    f"v{updated['current_version'].get('version_num', 1)}"
                )
                await self._broadcast_work(response, "task_done")
                if self.room_manager and task_id:
                    self.room_manager.record_task_completed(task_id, response, self.name, self.emoji)
                return response
            except ValueError as e:
                msg = f"ℹ️ {e}"
                await self._broadcast_work(msg, "message")
                return msg

        if action == "publish":
            pub = publish_project(pid)
            if pub:
                response = (
                    f"📦 Опубликовано · «{pub.get('title')}» — handoff готов (tokens + React)."
                )
                await self._broadcast_work(response, "task_done")
                if self.room_manager and task_id:
                    self.room_manager.record_task_completed(task_id, response, self.name, self.emoji)
                if self.room_manager:
                    handoff = pub.get("figma_handoff") or {}
                    await self.room_manager.broadcast_work({
                        "type": "sonya_studio_published",
                        "agent_id": self.agent_id,
                        "agent_name": self.name,
                        "agent_emoji": self.emoji,
                        "project_id": pid,
                        "project_title": pub.get("title"),
                        "message": response,
                        "handoff": handoff,
                        "timestamp": handoff.get("published_at"),
                    })
                return response

        return None
