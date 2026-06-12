from datetime import datetime
import random
from agents.base_agent import BaseAgent
from agents.react_preview import generate_react_preview, is_polish_task, is_site_task
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

        import config as cfg_module
        from integrations.figma_oauth import is_figma_connected

        if cfg_module.config.get("figma_study_enabled", True) and is_figma_connected():
            if random.random() < 0.55:
                from integrations.figma_learning import run_figma_study_session, run_figma_create_session

                self.status = "learning"
                self.location = "library"
                action = random.choices(["study", "create"], weights=[0.72, 0.28])[0]
                try:
                    if action == "create":
                        ok = await run_figma_create_session(self)
                        if ok:
                            self.figma_creations += 1
                    else:
                        ok = await run_figma_study_session(self)
                        if ok:
                            self.figma_studies += 1
                finally:
                    self.location = "studio"
                    self.status = "idle"
                    if self.room_manager:
                        await self.room_manager.send_agents_state()
                await self._interruptible_sleep(self._learning_delay())
                return

        await super()._learn()

    async def apply_figma_design(self, figma_result: dict):
        """Применить импортированный макет Figma."""
        self.last_figma = figma_result
        summary = figma_result.get("summary", {})
        task_text = f"UI по макету Figma: {summary.get('file_name', 'Design')}"
        colors = summary.get("colors", [])
        color_hint = ", ".join(colors[:5]) if colors else ""
        enhanced = f"{task_text}. Цвета: {color_hint}. Адаптивный React-компонент."
        await self._emit_preview(enhanced)
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

    def _figma_colors(self) -> list[str]:
        if not self.last_figma:
            return []
        summary = self.last_figma.get("summary", {})
        return summary.get("colors") or self.last_figma.get("colors") or []

    def _build_preview(self, task_text: str) -> dict:
        figma_colors = self._figma_colors()
        previous = self.last_preview if is_polish_task(task_text) else None
        preview = generate_react_preview(task_text, figma_colors=figma_colors, previous=previous)
        preview["task"] = task_text
        preview["timestamp"] = datetime.now().isoformat()
        self.last_preview = preview
        return preview

    async def _emit_preview(self, task_text: str):
        preview = self._build_preview(task_text)
        if preview.get("is_site") or is_site_task(task_text):
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
                "polished": preview.get("polished", False),
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

    async def handle_direct_chat(self, text: str):
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

        await self._emit_preview(text)

        response = self.build_task_response(text, self._find_relevant_knowledge(text))
        response += f"\n\n🖥️ **React Preview** обновлён — смотрите панель «{self.last_preview['title']}»."

        self.direct_chat.append({
            "role": "agent",
            "text": response,
            "timestamp": datetime.now().isoformat()
        })
        from direct_chat_store import DirectChatStore
        DirectChatStore.save(self.agent_id, self.direct_chat)

        if self.room_manager:
            await self.room_manager.broadcast({
                "type": "direct_agent_message",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": response,
                "status": self.status,
                "location": self.location,
                "timestamp": datetime.now().isoformat()
            })

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

        response = ""
        try:
            figma_url = self._extract_figma_url(task_text)
            if figma_url:
                client = await get_client_async()
                if client.configured:
                    try:
                        figma_data = await client.import_design(figma_url)
                        await self.apply_figma_design(figma_data)
                    except Exception as e:
                        await self._broadcast_work(f"⚠️ Figma: {e}", "error")

            await self._emit_preview(task_text)

            response = self.build_task_response(task_text, self._find_relevant_knowledge(task_text))
            if self.last_preview and (self.last_preview.get("is_site") or is_site_task(task_text)):
                response += (
                    f"\n\n🌐 **Сайт готов!**\n"
                    f"• Нажмите **🎨 Preview** в шапке — живой просмотр\n"
                    f"• Или откройте в браузере: /api/sites/latest"
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
