from agents.base_agent import BaseAgent


class PresenterAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="presenter",
            name="Ника",
            role="Presentation Designer",
            emoji="📽️",
            description=(
                "Ты эксперт по презентациям и питчам. Создаёшь slide decks, "
                "storytelling для стейкholdеров, investor pitch и tech talks. "
                "HTML-слайды, структура, визуальная иерархия."
            ),
            room_manager=room_manager,
        )

    def get_responsibilities(self) -> str:
        return (
            "- Презентации и pitch decks\n"
            "- Структура слайдов и storytelling\n"
            "- Tech talks и demo days\n"
            "- Визуальная подача продуктов"
        )

    def get_fallback_responses(self) -> list:
        return [
            "📽️ Готовлю презентацию: '{task}'.\n\nСтруктура:\n1. Hook\n2. Problem\n3. Solution\n4. Demo\n5. CTA",
            "📽️ Слайды по '{task}' — делаю HTML deck с 5–8 слайдами.",
        ]
