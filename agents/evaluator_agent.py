"""Агент-оценщик навыков команды."""

from agents.base_agent import BaseAgent


class EvaluatorAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="evaluator",
            name="Маша",
            role="Skill Evaluator & Quality Coach",
            emoji="🎓",
            description=(
                "Ты оцениваешь работу команды: навыки, качество артефактов, "
                "соответствие задаче. Даёшь конструктивную обратную связь "
                "и баллы 1–10. Помогаешь агентам расти через обучение."
            ),
            room_manager=room_manager,
        )
        self.skill_scores: dict[str, list] = {}

    def get_responsibilities(self) -> str:
        return (
            "- Оценка результатов агентов\n"
            "- Обратная связь по обучению и практике\n"
            "- Рекомендации по улучшению\n"
            "- Подтверждение готовности к показу пользователю"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🎓 Оцениваю «{task}»: проверяю соответствие роли и качество.",
            "🎓 «{task}» — даю баллы и рекомендации команде.",
        ]

    async def evaluate_output(
        self,
        task_text: str,
        agent_id: str,
        agent_name: str,
        response: str,
        context: str = "task",
    ) -> dict:
        """Оценка работы агента — LLM или эвристика."""
        score = 7
        feedback = f"Работа по «{task_text[:80]}» в целом соответствует роли."
        try:
            from integrations.llm_client import is_configured, agent_reply
            if is_configured():
                prompt = (
                    f"Оцени работу агента {agent_name} ({agent_id}) по задаче: {task_text}\n"
                    f"Контекст: {context}\nОтвет/результат:\n{response[:1500]}\n"
                    "Дай балл 1-10 и 2-3 предложения feedback на русском."
                )
                raw = await agent_reply(self.name, self.role, self.description, prompt, [])
                feedback = raw.strip()
                for n in range(10, 0, -1):
                    if str(n) in raw[:80]:
                        score = n
                        break
        except Exception:
            pass

        self.skill_scores.setdefault(agent_id, []).append({
            "score": score,
            "task": task_text[:100],
            "context": context,
        })
        if len(self.skill_scores[agent_id]) > 50:
            self.skill_scores[agent_id] = self.skill_scores[agent_id][-50:]

        if context in ("peer_learning", "learning_practice", "learning", "task"):
            try:
                from room.learning_projects import LearningProjects
                LearningProjects().add_evaluation(
                    agent_id, score, feedback, task=task_text[:200], context=context,
                )
            except Exception:
                pass

        return {"score": score, "feedback": feedback, "agent_id": agent_id}
