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
            "📽️ Презентация по «{task}» готова.\n\nФайл **presentation.pptx** — скачайте по ссылке в чате или во вкладке **Проекты**.",
            "📽️ Слайды для «{task}» собраны.\n\nPowerPoint (.pptx) приложен к результату — не React-сайт.",
            "📽️ «{task}» — deck из 6–8 слайдов.\n\nСкачайте **presentation.pptx** и откройте в PowerPoint / Google Slides.",
        ]
