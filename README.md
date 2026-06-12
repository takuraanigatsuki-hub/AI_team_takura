# AI Team Room (AI_team_takura)

Виртуальная команда из 9 ИИ-агентов: PM, архитектор, backend, frontend, QA, ревьюер, документация, DevOps и Cursor SDK (Лео).

## Возможности

- **3D-студия** — аватары, speech bubbles, confetti, mini-map, день/ночь
- **Рабочий чат** + streaming LLM-ответов (OpenAI-compatible)
- **Kanban** и **Timeline / Replay**
- **PM Виктор** — план, debates Architect vs Reviewer
- **React Preview** + Figma compare + Deploy ZIP
- **Standup** + Voice (TTS/STT)
- **Cursor Cloud Agent** + GitHub auto-sync
- **Интеграции**: Telegram, Jira, Linear, Notion, Vercel (опционально)
- **PWA** — установка на телефон, push-уведомления
- **Docker** — `docker compose up --build`

## Быстрый запуск (Windows)

```powershell
.\run.bat
# или
.\scripts\run.ps1
```

## Ручной запуск

```bash
pip install -r requirements.txt
python main.py
```

Откройте http://localhost:8000

## Переменные окружения (.env)

Скопируйте `.env.example` → `.env`:

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | Реальные ответы агентов (без ключа — шаблоны) |
| `CURSOR_API_KEY` | Cursor Cloud Agent (Лео) |
| `FIGMA_*` | Figma OAuth / token |
| `TELEGRAM_*` | Уведомления + webhook |
| `ROOM_API_KEY` | Опциональная защита POST /api/task |

## Тесты

```bash
python -m pytest tests/test_smoke.py -q
```

## Стек

Python · FastAPI · WebSocket · Three.js · Cursor SDK
