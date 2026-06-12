import os
from datetime import datetime

from agents.base_agent import BaseAgent
from integrations.cursor_client import get_client


CODING_KEYWORDS = [
    "код", "code", "рефактор", "refactor", "исправ", "fix", "bug", "баг",
    "implement", "реализ", "напиши", "добавь", "создай файл", "pull request",
    "pr", "commit", "функци", "class", "модул", "api endpoint", "cursor",
]


class CursorAgent(BaseAgent):
    """Агент для coding-задач через Cursor SDK / Cloud Agents API."""

    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="cursor",
            name="Лео",
            role="Cursor AI Developer",
            emoji="⚡",
            description=(
                "Ты coding-агент на базе Cursor SDK. Пишешь и рефакторишь код "
                "в локальном проекте или cloud-репозитории. Используешь те же модели, "
                "что и Cursor IDE — composer, semantic search, subagents."
            ),
            room_manager=room_manager,
        )
        self.last_run = None

    def get_responsibilities(self) -> str:
        return (
            "- Написание и рефакторинг кода через Cursor SDK\n"
            "- Исправление багов и code review с AI\n"
            "- Cloud Agent для GitHub-репозиториев\n"
            "- Интеграция с CI/CD и автоматизация задач"
        )

    def get_fallback_responses(self) -> list:
        return [
            "⚡ Задача '{task}' отправлена в Cursor Agent.\n\nПроверьте панель **Cursor** в шапке для статуса.",
            "⚡ '{task}' — coding-задача принята.\n\nЛокальный агент работает над проектом.",
            "⚡ Выполнил '{task}' через Cursor SDK.\n\nРезультат в рабочем чате и панели Cursor.",
        ]

    @staticmethod
    def is_coding_task(text: str) -> bool:
        t = text.lower()
        return any(k in t for k in CODING_KEYWORDS)

    async def _broadcast_cursor_event(self, message: str, event_type: str = "cursor_progress"):
        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": event_type,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            })

    async def _process_task(self, task: dict):
        from config import config

        self.status = "working"
        self.location = "studio"
        self.current_task = task
        task_text = task.get("text", "")
        sender = task.get("sender", "Пользователь")
        task_id = task.get("task_id")

        if self.room_manager and task_id:
            self.room_manager.record_task_started(task_id)

        await self._broadcast_work(
            f"📋 Coding-задача от {sender}: *{task_text}*\nЗапускаю Cursor Agent…",
            "task_received",
        )

        response = ""
        try:
            if not config.get("cursor_enabled"):
                raise RuntimeError(
                    "Cursor SDK не настроен. Добавьте CURSOR_API_KEY в `.env`."
                )

            if config.get("cursor_github_sync"):
                response = (
                    "⚡ Задача уже отправлена в **GitHub Sync** (Cursor Cloud Agent).\n"
                    "Следите за сообщениями «GitHub Sync» в чате — там будет ссылка на PR."
                )
                await self._broadcast_work(f"✅ {response}", "task_done")
                if self.room_manager and task_id:
                    self.room_manager.record_task_completed(task_id, response, self.name, self.emoji)
                return

            client = get_client()
            verify = await client.verify_key()
            if not verify.get("ok"):
                raise RuntimeError(f"Cursor API: {verify.get('error', 'ошибка ключа')}")

            async def on_progress(msg: str):
                await self._broadcast_cursor_event(msg)

            from integrations.github_sync import resolve_repo_url

            repo_url = await resolve_repo_url()
            ref = config.get("cursor_repo_ref", "main")
            auto_pr = config.get("cursor_auto_create_pr", True)
            cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            run = await client.run_task(
                prompt=task_text,
                repo_url=repo_url,
                ref=ref,
                cwd=cwd,
                auto_create_pr=auto_pr,
                on_progress=on_progress,
                force_cloud=bool(repo_url),
            )
            self.last_run = run

            agent_id = run.get("agent_id")
            if agent_id:
                from integrations.github_sync import active_cloud_agents
                active_cloud_agents[agent_id] = {
                    "run_id": run.get("id"),
                    "prompt": task_text[:500],
                    "repo_url": repo_url,
                    "started_at": run.get("started_at"),
                }

            text = run.get("text", "Задача выполнена.")
            mode = run.get("mode", "local")
            run_id = run.get("id", "")

            response = (
                f"⚡ **Cursor Agent** ({mode})\n\n{text}\n\n"
                f"Run ID: `{run_id}`"
            )

            if self.room_manager:
                await self.room_manager.broadcast_work({
                    "type": "cursor_run_done",
                    "run_id": run_id,
                    "mode": mode,
                    "status": run.get("status"),
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "agent_emoji": self.emoji,
                    "message": text[:2000],
                    "timestamp": datetime.now().isoformat(),
                })

            await self._broadcast_work(f"✅ Выполнено:\n{response}", "task_done")
            if self.room_manager and task_id:
                self.room_manager.record_task_completed(task_id, response, self.name, self.emoji)

        except Exception as e:
            err = str(e)
            await self._broadcast_work(f"❌ Ошибка Cursor: {err}", "error")
            if self.room_manager and task_id:
                self.room_manager.record_task_failed(task_id, err)
        finally:
            if self.room_manager:
                await self.room_manager._broadcast_task_history()
            self.memory.append({
                "task": task_text,
                "response": response,
                "run": self.last_run,
                "timestamp": datetime.now().isoformat(),
            })
            self.status = "idle"
            self.current_task = None

    def get_state(self) -> dict:
        state = super().get_state()
        state["has_cursor_run"] = self.last_run is not None
        state["cursor_status"] = (self.last_run or {}).get("status")
        return state
