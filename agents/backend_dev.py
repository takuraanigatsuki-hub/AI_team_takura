from agents.base_agent import BaseAgent


class BackendDevAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="backend",
            name="Макс",
            role="Backend Developer",
            emoji="⚙️",
            description=(
                "Ты senior backend разработчик. Специализируешься на Python, Go, "
                "PostgreSQL, Redis, Kafka. Пишешь чистый, производительный код. "
                "Обожаешь оптимизацию запросов и асинхронное программирование. "
                "Прагматик — выбираешь простые решения сложных проблем."
            ),
            room_manager=room_manager
        )

    def get_responsibilities(self) -> str:
        return (
            "- Разработка серверной логики и API\n"
            "- Проектирование и оптимизация баз данных\n"
            "- Интеграция с внешними сервисами\n"
            "- Оптимизация производительности\n"
            "- Написание миграций БД\n"
            "- Реализация бизнес-логики"
        )

    def get_fallback_responses(self) -> list:
        return [
            "⚙️ Берусь за задачу: '{task}'.\n\nПлан реализации:\n```python\n# Создаю endpoint\n@router.post('/api/resource')\nasync def create_resource(data: Schema, db: Session = Depends()):\n    return await service.create(data, db)\n```\nДобавлю валидацию, обработку ошибок и логирование.",
            "⚙️ Задача '{task}' — понял.\n\nРеализую:\n1. REST endpoint с Pydantic валидацией\n2. Слой сервисов с бизнес-логикой\n3. Repository pattern для работы с БД\n4. Кэширование через Redis\n\nОжидай PR через ~2 часа.",
            "⚙️ Анализирую '{task}'.\n\nБуду использовать:\n• FastAPI + asyncpg для максимальной производительности\n• Индексы в PostgreSQL для оптимизации запросов\n• Connection pooling для масштабируемости\n\nПишу код и тесты параллельно."
        ]
