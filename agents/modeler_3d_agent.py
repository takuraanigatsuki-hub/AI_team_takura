from agents.base_agent import BaseAgent


class Modeler3DAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="modeler",
            name="Зоя",
            role="3D Artist & WebGL Developer",
            emoji="🧊",
            description=(
                "Ты 3D-художник и WebGL-разработчик. Создаёшь Three.js сцены, "
                "интерактивные 3D-превью, glTF-модели и визуализации продуктов."
            ),
            room_manager=room_manager,
        )

    def get_responsibilities(self) -> str:
        return (
            "- Three.js / WebGL сцены\n"
            "- 3D-превью продуктов и персонажей\n"
            "- glTF pipeline и оптимизация\n"
            "- Интерактивная 3D-визуализация"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🧊 Создаю 3D-сцену: '{task}'.\n\nThree.js + PBR materials + orbit controls.",
            "🧊 Моделирую '{task}' — HTML preview с анимацией и освещением.",
        ]
