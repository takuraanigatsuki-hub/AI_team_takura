from datetime import datetime
from agents.base_agent import BaseAgent
from agents.react_preview import generate_react_preview, is_site_task
from site_exporter import export_site_html


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
        return state
