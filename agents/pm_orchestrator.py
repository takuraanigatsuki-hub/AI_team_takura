import random
from agents.base_agent import BaseAgent

WORK_MSG = "work"


class PMOrchestratorAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="pm",
            name="Виктор",
            role="Project Manager & Orchestrator",
            emoji="🎯",
            description=(
                "Ты PM и оркестратор команды. Координируешь работу всех агентов, "
                "отслеживаешь прогресс, управляешь приоритетами. "
                "Используешь Agile/Scrum методологию. "
                "Умеешь разбивать большие задачи на подзадачи и распределять по команде."
            ),
            room_manager=room_manager
        )
        self.sprint_tasks = []
        self.completed_tasks = []

    def get_responsibilities(self) -> str:
        return (
            "- Координация работы команды\n"
            "- Планирование спринтов и задач\n"
            "- Распределение задач между агентами\n"
            "- Отслеживание прогресса и метрик\n"
            "- Управление рисками и блокерами\n"
            "- Коммуникация с заказчиком"
        )

    def create_plan(self, task_text: str, assignments: dict, agents: dict) -> str:
        task_lower = task_text.lower()
        goal = task_text
        if any(w in task_lower for w in ["сайт", "website", "лендинг"]):
            goal = f"Создать рабочий сайт: {task_text}"
        elif any(w in task_lower for w in ["api", "бэкенд", "backend"]):
            goal = f"Реализовать backend/API: {task_text}"
        else:
            goal = f"Выполнить: {task_text}"

        lines = [
            "📋 **ПЛАН РАБОТЫ**",
            f"**Заказ:** {task_text}",
            f"**Цель:** {goal}",
            "",
            "**Этапы:**",
        ]
        for i, (agent_id, subtask) in enumerate(assignments.items(), 1):
            a = agents.get(agent_id)
            if a:
                lines.append(f"{i}. {a.emoji} **{a.name}** — {subtask}")

        lines += [
            "",
            "**Критерии готовности:**",
            "• Все этапы выполнены и проверены ревьюером",
            "• Результат виден в чате и вкладке «Задачи»",
            "• Для UI — React Preview / готовый сайт",
            "",
            "👂 **Команда, слушайте план и приступайте!**",
        ]
        return "\n".join(lines)

    async def orchestrate_task(self, task_text: str, agents: dict, parent_id: str = None):
        assignments = self._analyze_and_assign(task_text, agents)

        plan = self.create_plan(task_text, assignments, agents)

        if self.room_manager:
            self.room_manager.current_plan = {
                "task": task_text,
                "plan": plan,
                "assignments": assignments,
                "parent_id": parent_id,
            }
            await self.room_manager.broadcast_work({
                "type": "pm_plan",
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": plan,
                "task": task_text,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })

        for agent_id, subtask in assignments.items():
            if agent_id in agents:
                child_id = None
                if self.room_manager and parent_id:
                    child_id = self.room_manager.task_history.add_queued(
                        subtask, agent_id,
                        agents[agent_id].name, agents[agent_id].emoji,
                        parent_id=parent_id, sender="PM Виктор"
                    )
                await agents[agent_id].assign_task(
                    subtask, sender="PM Виктор",
                    parent_id=parent_id, task_id=child_id
                )
                await self._broadcast_work(
                    f"📌 {agents[agent_id].emoji} {agents[agent_id].name} — взял пункт плана:\n*{subtask}*",
                    "assignment"
                )

        if parent_id and self.room_manager:
            p = self.room_manager.task_history._find(parent_id)
            if p and p["status"] == "submitted":
                p["status"] = "in_progress"
                p["started_at"] = __import__("datetime").datetime.now().isoformat()
                self.room_manager.task_history._save()

        self.sprint_tasks.append({"task": task_text, "assignments": assignments, "plan": plan})
        if self.room_manager:
            await self.room_manager.pipeline.start(task_text, assignments, agents)
            from room.debate_engine import maybe_start_debate
            await maybe_start_debate(task_text, assignments, agents, self.room_manager)
            await self._notify_external(task_text, assignments)
            await self.room_manager._broadcast_task_history()

    async def _notify_external(self, task_text: str, assignments: dict):
        try:
            from integrations.external_hub import send_telegram, create_jira_issue, create_linear_issue
            import config as cfg
            summary = task_text[:120]
            agents_list = ", ".join(assignments.keys())
            msg = f"📋 *AI Team*\n{summary}\nАгенты: {agents_list}"
            if cfg.config.get("telegram_notify_tasks"):
                await send_telegram(msg)
            if cfg.config.get("jira_auto_create"):
                await create_jira_issue(summary, f"Задача: {task_text}\nАгенты: {agents_list}")
            if cfg.config.get("linear_auto_create"):
                await create_linear_issue(summary, task_text[:500])
        except Exception:
            pass

    async def _broadcast_work(self, message: str, msg_type: str = "message"):
        if self.room_manager:
            await self.room_manager.broadcast_work({
                "type": msg_type,
                "agent_id": self.agent_id,
                "agent_name": self.name,
                "agent_emoji": self.emoji,
                "message": message,
                "status": self.status,
                "location": self.location,
                "timestamp": __import__("datetime").datetime.now().isoformat(),
            })

    def _analyze_and_assign(self, task_text: str, agents: dict) -> dict:
        task_lower = task_text.lower()
        assignments = {}

        if any(w in task_lower for w in [
            "сайт", "website", "веб-сайт", "web-сайт", "web site",
            "лендинг", "landing", "портал", "веб-страниц", "webpage", "веб приложен"
        ]):
            assignments["architect"] = f"Спроектировать структуру сайта: {task_text}"
            assignments["frontend"] = f"Сверстать сайт на React: {task_text}"
            assignments["backend"] = f"Подготовить API для сайта: {task_text}"
            assignments["qa"] = f"Протестировать сайт: {task_text}"
            assignments["doc_writer"] = f"Документация сайта: {task_text}"
            assignments["reviewer"] = f"Проверить качество сайта: {task_text}"
            return assignments

        if any(w in task_lower for w in ["архитектур", "систем", "структур"]):
            assignments["architect"] = f"Спроектировать архитектуру: {task_text}"

        if any(w in task_lower for w in ["api", "бэкенд", "backend", "сервер", "база", "бд"]):
            assignments["backend"] = f"Реализовать backend: {task_text}"

        if any(w in task_lower for w in [
            "интерфейс", "ui", "фронтенд", "frontend", "компонент", "страниц",
            "кнопк", "форм", "react", "верст", "дизайн", "css", "landing", "макет"
        ]):
            assignments["frontend"] = f"Разработать интерфейс: {task_text}"

        if any(w in task_lower for w in ["тест", "test", "баг", "bug", "качество", "проверь"]):
            assignments["qa"] = f"Написать тесты: {task_text}"

        if any(w in task_lower for w in ["докумен", "readme", "описани", "инструкци"]):
            assignments["doc_writer"] = f"Документировать: {task_text}"

        if any(w in task_lower for w in ["деплой", "deploy", "kubernetes", "docker", "ci/cd", "инфраструктур"]):
            assignments["devops"] = f"Настроить деплой: {task_text}"

        if any(w in task_lower for w in [
            "код", "code", "рефактор", "refactor", "исправ", "fix", "bug", "баг",
            "implement", "напиши", "cursor", "sdk", "функци", "class", "модул",
        ]):
            try:
                from config import config
                if not config.get("cursor_github_sync"):
                    assignments["cursor"] = f"Coding через Cursor SDK: {task_text}"
            except Exception:
                assignments["cursor"] = f"Coding через Cursor SDK: {task_text}"

        if any(w in task_lower for w in ["figma", "макет", "design token", "дизайн-систем"]):
            assignments["frontend"] = f"Импорт из Figma + UI: {task_text}"

        if not assignments:
            assignments["architect"] = f"Спланировать: {task_text}"
            assignments["backend"] = f"Реализовать: {task_text}"
            assignments["frontend"] = f"Сделать UI: {task_text}"

        assignments["reviewer"] = f"Проверить результат: {task_text}"
        return assignments

    def get_fallback_responses(self) -> list:
        return [
            "🎯 План по '{task}' опубликован в рабочем чате. Команда приступает.",
            "🎯 Задача '{task}' разбита на этапы — смотрите план выше.",
            "🎯 '{task}' в работе. Следите за прогрессом во вкладке «Задачи».",
        ]
