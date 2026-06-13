# AI Team Room (AI_team_takura)

**Автономная платформа с командой из 13 ИИ-агентов** — от идеи и дизайна до кода, тестов, презентаций и деплоя. Командный чат, Kanban, вкладка **Обучение** (проекты агентов на проверку), Figma → React, Cursor SDK, GitHub sync, **Android companion** и нативный **Windows-установщик с updater**.

## Что умеет проект

### 🤖 Команда агентов (13 ролей)

| Агент | Роль |
|-------|------|
| 👔 PM (Виктор) | Планирование, декомпозиция задач, спринты, оркестрация команды |
| 🏛️ Architect | Архитектура, C4, API design, ADR, диаграммы |
| ⚙️ Backend | FastAPI, PostgreSQL, REST/gRPC, сервисы и API |
| 🎨 Frontend | React, TypeScript, UI/UX, вёрстка, Figma → код |
| 🧪 QA | pytest, Playwright, нагрузочные тесты, чек-листы |
| 🔍 Reviewer | Code review, SOLID, рефакторинг, безопасность кода |
| 📝 Doc Writer | README, OpenAPI, гайды, техническая документация |
| 🔧 DevOps | Docker, CI/CD, GitHub Actions, инфраструктура |
| ⚡ Cursor (Лео) | AI-кодинг, Cloud Agent, GitHub PR |
| 📽️ Presenter | Pitch deck, слайды, HTML-презентации |
| 🧊 3D Modeler | Three.js, glTF (артефакты обучения, не отдельная 3D-студия) |
| 📊 Evaluator | Оценка качества работы агентов, коучинг |
| 🛡️ Security | OWASP, аудит, мониторинг угроз (только admin) |

### 🎮 Интерфейс и рабочие пространства

- **Обучение** — агенты сдают проекты на проверку (как Sonya Studio), лента обучения и Design Lab для admin
- **Командный чат** — streaming LLM-ответов, @mentions, история задач
- **Kanban & Sprint** — backlog, приоритеты, burndown, статусы задач
- **Timeline / Replay** — хронология событий комнаты
- **Dashboard** — центр управления: задачи, интеграции, статистика
- **React Preview** — живой предпросмотр UI прямо в приложении
- **Sonya Figma Studio** — импорт макетов, Compare (Figma vs React), pipeline deploy
- **Investor Portal** — отдельный режим для инвесторов
- **Android companion** — `/mobile` и APK (Capacitor); iOS позже
- **PWA** — установка на телефон, push-уведомления

### ⚙️ Разработка и автоматизация

- **PM-оркестрация** — автоматическая декомпозиция задач и назначение агентов
- **React Preview + Deploy ZIP** — сборка и выдача артефактов
- **Cursor Cloud Agent** — удалённое написание кода и PR на GitHub
- **GitHub Auto-Sync** — commit + push при изменениях (admin)
- **Knowledge sync** — `knowledge/*.json` и учебные проекты автоматически в репозиторий
- **RAG knowledge base** — база знаний по ролям агентов
- **QA Playwright** — автотесты UI в браузере
- **Docker Sandbox** — изолированное выполнение кода
- **ReAct loop** — plan → tool → observe для сложных задач
- **Standup + Voice** — голосовые standup-сессии (TTS/STT)

### 🖥️ Desktop (Windows)

- **Установщик** `dist/AI_Team_Room_Setup.exe` — тёмный UI, ярлыки, регистрация в системе
- **Updater** `AI_Team_Room_Updater.exe` — скачивает свежий setup с сервера
- **Uninstaller** `AI_Team_Room_Uninstall.exe` — удаление в том же стиле, что установщик
- Сборка: `.\scripts\build-desktop.ps1`

### 👥 Пользователи и администрирование

- **Регистрация / вход** — email или username, уникальные имена
- **Подписки и баланс** — тарифы, кредиты, billing
- **Роли**: owner, admin, tech_admin, support, investor, member
- **Admin-панель** — пользователи, блокировка, сессии, привилегии
- **Система поддержки** — тикеты, чат с оператором, guest-report на лендинге

### 🔗 Интеграции

Figma · Cursor SDK · GitHub · Linear · Jira · Notion · Vercel · Telegram (опционально) · Microsoft 365

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

Откройте http://localhost:8000 — главная страница, `/workspace` — приложение, `/mobile` — companion.

## Переменные окружения (.env)

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | LLM-ответы агентов |
| `CURSOR_API_KEY` | Cursor Cloud Agent |
| `FIGMA_*` | Figma OAuth / token |
| `TELEGRAM_*` | Опциональные уведомления (legacy) |
| `ROOM_API_KEY` | Защита POST /api/task |

## Тесты

```bash
python -m pytest tests/ -q
```

## Production (VPS 24/7)

```bash
bash scripts/install-server.sh
bash scripts/deploy-vps.sh
```

Подробно: [docs/DEPLOY.md](docs/DEPLOY.md) · Android: [android-companion/README.md](android-companion/README.md)
