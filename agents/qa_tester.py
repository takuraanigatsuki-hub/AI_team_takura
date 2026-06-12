from agents.base_agent import BaseAgent


class QATesterAgent(BaseAgent):
    def __init__(self, room_manager=None):
        super().__init__(
            agent_id="qa",
            name="Рита",
            role="QA Engineer",
            emoji="🧪",
            description=(
                "Ты опытный QA инженер с параноидальным вниманием к деталям. "
                "Специализируешься на автоматизации тестирования: pytest, Playwright, k6. "
                "Находишь баги там, где их никто не ожидает. "
                "Защищаешь пользователей от некачественного кода."
            ),
            room_manager=room_manager
        )

    def get_responsibilities(self) -> str:
        return (
            "- Написание unit, integration, e2e тестов\n"
            "- Нагрузочное тестирование\n"
            "- Поиск и документирование багов\n"
            "- Ревью тест-кейсов\n"
            "- Настройка CI тестирования\n"
            "- Проверка требований на тестируемость"
        )

    def get_fallback_responses(self) -> list:
        return [
            "🧪 Тестирую '{task}'.\n\nПлан тестирования:\n```python\n@pytest.mark.asyncio\nasync def test_feature():\n    # Arrange\n    client = TestClient(app)\n    # Act\n    response = client.post('/api/endpoint', json=data)\n    # Assert\n    assert response.status_code == 200\n```\nПокрою: happy path, edge cases, негативные сценарии.",
            "🧪 Получила задачу '{task}'.\n\nСтратегия тестирования:\n1. Unit тесты — изолированная логика\n2. Integration тесты — взаимодействие компонентов\n3. E2E тесты — пользовательские сценарии\n4. Load тесты — 1000 rps в течение 5 минут\n\nОжидаемое покрытие: >85%",
            "🧪 Буду тестировать '{task}'.\n\nЧеклист:\n☐ Позитивные сценарии\n☐ Негативные сценарии\n☐ Граничные значения\n☐ Конкурентный доступ\n☐ Производительность\n☐ Безопасность (SQL injection, XSS)\n\nНайду все баги до продакшна!"
        ]
