from agents.base_agent import BaseAgent
from room.task_routing import classify_task_kind


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
        kind = classify_task_kind(task_text)
        goal_map = {
            "presentation": f"Подготовить презентацию: {task_text}",
            "model_3d": f"Создать 3D-сцену: {task_text}",
            "table": f"Сделать таблицу данных: {task_text}",
            "site": f"Создать рабочий сайт: {task_text}",
            "api": f"Реализовать backend/API: {task_text}",
            "ui": f"Сделать UI-компонент: {task_text}",
        }
        goal = goal_map.get(kind, f"Выполнить: {task_text}")

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

        criteria = ["• Все этапы выполнены и проверены ревьюером", "• Результат виден в чате и вкладке «Задачи»"]
        if kind == "site":
            criteria.append("• Для UI — React Preview / готовый сайт")
        elif kind == "presentation":
            criteria.append("• Презентация — слайды в «Проекты» + Microsoft 365 (если настроен)")
        elif kind == "model_3d":
            criteria.append("• 3D — интерактивная сцена Three.js")
        elif kind == "table":
            criteria.append("• Таблица — React Preview + Excel в Microsoft 365 (если настроен)")

        lines += ["", "**Критерии готовности:**"] + criteria
        lines += ["", "👂 **Команда, слушайте план и приступайте!**"]
        return "\n".join(lines)

    async def orchestrate_task(self, task_text: str, agents: dict, parent_id: str = None):
        assignments = self._analyze_and_assign(task_text, agents)

        from room.role_triage import run_role_triage
        assignments = await run_role_triage(
            task_text, assignments, agents, self.room_manager, parent_id,
        )

        plan = self.create_plan(task_text, assignments, agents)
        plan += "\n\n🔍 **Triage:** каждый агент проверил роль — работают только подходящие."

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
        kind = classify_task_kind(task_text)
        assignments: dict[str, str] = {}

        if kind == "presentation":
            assignments["presenter"] = f"Создать презентацию (слайды): {task_text}"
            assignments["doc_writer"] = f"Тексты слайдов и заметки: {task_text}"
            assignments["reviewer"] = f"Проверить презентацию: {task_text}"
            return assignments

        if kind == "model_3d":
            assignments["modeler"] = f"Создать 3D-сцену: {task_text}"
            assignments["reviewer"] = f"Проверить 3D-результат: {task_text}"
            return assignments

        if kind == "table":
            assignments["frontend"] = f"Сверстать таблицу данных (React, не landing): {task_text}"
            assignments["evaluator"] = f"Оценить таблицу и навыки: {task_text}"
            return assignments

        if kind == "site":
            assignments["architect"] = f"Спроектировать структуру сайта: {task_text}"
            assignments["frontend"] = f"Сверстать сайт на React: {task_text}"
            assignments["backend"] = f"Подготовить API для сайта: {task_text}"
            assignments["qa"] = f"Протестировать сайт: {task_text}"
            assignments["doc_writer"] = f"Документация сайта: {task_text}"
            assignments["reviewer"] = f"Проверить качество сайта: {task_text}"
            return assignments

        if kind == "api":
            assignments["architect"] = f"Спроектировать API: {task_text}"
            assignments["backend"] = f"Реализовать backend: {task_text}"
            assignments["qa"] = f"Написать тесты API: {task_text}"
            assignments["reviewer"] = f"Code review API: {task_text}"
            return assignments

        if kind == "architecture":
            assignments["architect"] = f"Спроектировать архитектуру: {task_text}"
            assignments["reviewer"] = f"Проверить архитектуру: {task_text}"
            return assignments

        if kind == "tests":
            assignments["qa"] = f"Написать тесты: {task_text}"
            assignments["reviewer"] = f"Проверить покрытие: {task_text}"
            return assignments

        if kind == "infra":
            assignments["devops"] = f"Настроить инфраструктуру: {task_text}"
            assignments["reviewer"] = f"Проверить конфигурацию: {task_text}"
            return assignments

        if kind == "document":
            assignments["doc_writer"] = f"Документировать: {task_text}"
            assignments["reviewer"] = f"Проверить документ: {task_text}"
            return assignments

        if kind == "ui":
            assignments["frontend"] = f"Разработать UI-компонент: {task_text}"
            assignments["reviewer"] = f"Проверить UI: {task_text}"
            return assignments

        task_lower = task_text.lower()

        if any(w in task_lower for w in ["figma", "design token", "дизайн-систем"]):
            assignments["frontend"] = f"Импорт из Figma + UI: {task_text}"
            assignments["reviewer"] = f"Проверить UI: {task_text}"
            return assignments

        if any(w in task_lower for w in [
            "studio", "студия", "sonya studio", "design studio", "новый проект",
            "новый макет", "создай проект", "создай макет", "sonya design",
        ]):
            assignments["frontend"] = f"Sonya Studio — {task_text}"
            assignments["reviewer"] = f"Проверить проект: {task_text}"
            return assignments

        if any(w in task_lower for w in [
            "код", "code", "рефактор", "refactor", "implement", "cursor", "sdk",
        ]):
            try:
                from config import config
                if not config.get("cursor_github_sync"):
                    assignments["cursor"] = f"Coding через Cursor SDK: {task_text}"
            except Exception:
                assignments["cursor"] = f"Coding через Cursor SDK: {task_text}"

        if not assignments:
            assignments["architect"] = f"Спланировать подход: {task_text}"

        assignments.setdefault("reviewer", f"Проверить результат: {task_text}")
        return assignments

    def get_fallback_responses(self) -> list:
        return [
            "🎯 План по '{task}' опубликован в рабочем чате. Команда приступает.",
            "🎯 Задача '{task}' разбита на этапы — смотрите план выше.",
            "🎯 '{task}' в работе. Следите за прогрессом во вкладке «Задачи».",
        ]
