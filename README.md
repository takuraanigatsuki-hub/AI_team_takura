# AI Team Room (AI_team_takura)

**Автономная платформа с командой из 13 ИИ-агентов** — от идеи и дизайна до кода, тестов, презентаций и деплоя. Живая 3D-студия, командный чат, Kanban, Figma → React, Cursor SDK, GitHub sync и встроенная поддержка пользователей.

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
| 🧊 3D Modeler | Three.js, glTF, интерактивные 3D-сцены |
| 📊 Evaluator | Оценка качества работы агентов, коучинг |
| 🛡️ Security | OWASP, аудит, мониторинг угроз (только admin) |

### 🎮 Интерфейс и рабочие пространства

- **3D-студия** — аватары агентов на сцене, speech bubbles, confetti, mini-map, день/ночь
- **Командный чат** — streaming LLM-ответов, @mentions, история задач
- **Kanban & Sprint** — backlog, приоритеты, burndown, статусы задач
- **Timeline / Replay** — хронология событий комнаты
- **Dashboard** — центр управления: задачи, интеграции, статистика
- **React Preview** — живой предпросмотр UI прямо в приложении
- **Sonya Figma Studio** — импорт макетов, Compare (Figma vs React), pipeline deploy
- **Design Lab & Agent Learning** — обучение и улучшение агентов (admin)
- **Investor Portal** — отдельный режим для инвесторов
- **PWA** — установка на телефон, push-уведомления

### ⚙️ Разработка и автоматизация

- **PM-оркестрация** — автоматическая декомпозиция задач и назначение агентов
- **React Preview + Deploy ZIP** — сборка и выдача артефактов
- **Cursor Cloud Agent** — удалённое написание кода и PR на GitHub
- **GitHub Auto-Sync** — commit + push при изменениях (admin)
- **RAG knowledge base** — база знаний по ролям агентов
- **QA Playwright** — автотесты UI в браузере
- **Docker Sandbox** — изолированное выполнение кода
- **ReAct loop** — plan → tool → observe для сложных задач
- **Standup + Voice** — голосовые standup-сессии (TTS/STT)

### 👥 Пользователи и администрирование

- **Регистрация / вход** — личный кабинет, настройки, тема
- **Подписки и баланс** — тарифы, кредиты, billing
- **Роли**: owner, admin, tech_admin, support, investor, member
- **Admin-панель** — пользователи, блокировка, сессии, привилегии
- **Система поддержки** — тикеты, чат с оператором, готовые решения по темам
- **Скрытие технического UI** — GitHub, API-ключи, Cursor только для admin

### 🔗 Интеграции

Figma · Cursor SDK · GitHub · Telegram · Linear · Jira · Notion · Vercel · Microsoft 365 (опционально)

### 🛡️ Безопасность

- Security middleware, rate limiting, блокировка IP
- Фильтрация технических сообщений для обычных пользователей
- Audit log, security events

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

Откройте http://localhost:8000 — главная страница с описанием возможностей, `/app` — рабочее приложение.

## Переменные окружения (.env)

Скопируйте `.env.example` → `.env`:

| Переменная | Назначение |
|------------|------------|
| `OPENAI_API_KEY` | LLM-ответы агентов (OpenAI-compatible, Smart AIPI) |
| `CURSOR_API_KEY` | Cursor Cloud Agent (Лео) |
| `FIGMA_*` | Figma OAuth / token |
| `TELEGRAM_*` | Уведомления + bot |
| `ROOM_API_KEY` | Опциональная защита POST /api/task |

## Тесты

```bash
python -m pytest tests/ -q
```

## Production (VPS 24/7)

Сайт на сервере, управление из Cursor через Git push.

```bash
# на VPS (один раз)
bash scripts/install-server.sh
nano .env
bash scripts/deploy-vps.sh
```

Подробно: [docs/DEPLOY.md](docs/DEPLOY.md) — HTTPS, auto-deploy, бэкапы `data/`.

**Куда что подключить (DNS, GitHub Secrets, .env):** [docs/WHERE_TO_CONNECT.md](docs/WHERE_TO_CONNECT.md)

**Где купить VPS и домен за рубли:** [docs/HOSTING_RU.md](docs/HOSTING_RU.md)

Шаблон production `.env`: скопируйте `.env.production.example` → `.env` на VPS.

## Стек

Python · FastAPI · WebSocket · Three.js · Cursor SDK · Playwright · Docker
