# Где что подключить — пошаговая карта

Проект: **AI Team Room** · репозиторий: `takuraanigatsuki-hub/AI_team_takura`

---

## Схема (кто с кем связан)

```
┌─────────────┐     git push      ┌──────────────┐    SSH deploy    ┌─────────────┐
│ Cursor (ПК) │ ───────────────► │   GitHub     │ ───────────────► │  VPS 24/7   │
│  правки кода│                  │   main       │                  │   Docker    │
└─────────────┘                  └──────────────┘                  └──────┬──────┘
       │                                                                  │
       │ браузер                                                          │ HTTPS
       └──────────────────── https://room.ВАШ-ДОМЕН.ru/app ◄─────────────┘
```

| Место | Что там настраивается |
|-------|------------------------|
| **ПК (Cursor)** | Код, `git push`, локальный `.env` только для разработки |
| **GitHub** | Код + Secrets для auto-deploy |
| **VPS** | `.env`, Docker, данные `data/`, сайт 24/7 |
| **DNS регистратор** | Домен → IP сервера |
| **Smart AIPI / OpenAI** | Ключ LLM для агентов |
| **Figma** | OAuth для Design Lab |

---

## Шаг 1 — VPS (сервер)

### Где взять
Timeweb · Hetzner · DigitalOcean · Selectel — **Ubuntu 22.04**, 2 GB RAM.

### Что подключить на VPS

| Куда | Что |
|------|-----|
| Панель VPS → **Firewall** | Открыть порты **22**, **80**, **443** |
| SSH `root@IP_СЕРВЕРА` | Установка проекта (один раз) |

```bash
ssh root@ВАШ_IP
git clone https://github.com/takuraanigatsuki-hub/AI_team_takura.git
cd AI_team_takura
bash scripts/install-server.sh
cp .env.production.example .env
nano .env
bash scripts/deploy-vps.sh
docker compose -f docker-compose.prod.yml exec ai-team-room python scripts/create_owner.py
```

**Файл на сервере:** `~/AI_team_takura/.env` — главный конфиг production.  
Шаблон: `.env.production.example` в репозитории.

---

## Шаг 2 — Домен (DNS)

### Где настраивать
Регистратор домена (Reg.ru, Timeweb, Cloudflare, Namecheap…).

| Тип | Имя | Значение |
|-----|-----|----------|
| **A** | `room` (или `@`) | **IP вашего VPS** |

Пример: `room.mysite.ru` → `185.12.34.56`

### Куда прописать в проекте

| Файл | Переменная | Пример |
|------|------------|--------|
| VPS `.env` | `APP_DOMAIN` | `room.mysite.ru` |
| VPS `.env` | `FIGMA_REDIRECT_URI` | `https://room.mysite.ru/api/figma/callback` |

Проверка (через 5–30 мин после DNS):  
`https://room.mysite.ru/app`

---

## Шаг 3 — LLM (агенты отвечают по-настоящему)

### Где взять ключ

| Сервис | Где | Что скопировать |
|--------|-----|-----------------|
| **Smart AIPI** | [smartaipi.com](https://smartaipi.com) | API Key `sk-...` |
| OpenAI | platform.openai.com | API Key |

### Куда вставить

| Файл | Переменные |
|------|------------|
| **VPS** `~/AI_team_takura/.env` | `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL` |
| **ПК** `.env` (только для локальной разработки) | те же |

После изменения на VPS:
```bash
cd ~/AI_team_takura && bash scripts/deploy-vps.sh
```

---

## Шаг 4 — GitHub (код + auto-deploy)

### 4a. Репозиторий (уже есть)
`https://github.com/takuraanigatsuki-hub/AI_team_takura`

### 4b. С ПК — push кода

```powershell
cd C:\Users\USER\Desktop\AI_team_takura-main
.\scripts\deploy-from-pc.ps1 -Message "update"
```

Или: Cursor → Source Control → Commit → Push.

### 4c. Auto-deploy на VPS

**Где:** GitHub → репозиторий → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Откуда взять | Пример |
|--------|--------------|--------|
| `VPS_HOST` | IP или домен сервера | `185.12.34.56` |
| `VPS_USER` | SSH-пользователь | `root` |
| `VPS_SSH_KEY` | Приватный ключ (см. ниже) | `-----BEGIN OPENSSH...` |
| `VPS_PATH` | Папка проекта на сервере | `/root/AI_team_takura` |

#### SSH-ключ для GitHub Actions

**На ПК (PowerShell):**
```powershell
ssh-keygen -t ed25519 -f $env:USERPROFILE\.ssh\ai_team_deploy -N '""'
```

| Ключ | Куда |
|------|------|
| **Публичный** `ai_team_deploy.pub` | VPS: `~/.ssh/authorized_keys` |
| **Приватный** `ai_team_deploy` | GitHub Secret `VPS_SSH_KEY` (весь файл) |

После настройки: каждый `git push` в `main` → Actions → Deploy to VPS.

---

## Шаг 5 — Figma (Design Lab)

### Где
[figma.com](https://www.figma.com) → **Settings → OAuth apps** (или Personal Access Token).

### Куда

| Поле в Figma | Значение |
|--------------|----------|
| Redirect URI | `https://room.ВАШ-ДОМЕН.ru/api/figma/callback` |

| VPS `.env` | Значение |
|------------|----------|
| `FIGMA_CLIENT_ID` | из OAuth app |
| `FIGMA_CLIENT_SECRET` | из OAuth app |
| `FIGMA_REDIRECT_URI` | как выше |
| `FIGMA_ACCESS_TOKEN` | или PAT вместо OAuth |

---

## Шаг 6 — Cursor Agent (Лео)

| Где взять | cursor.com → Dashboard → API Keys |
|-----------|-----------------------------------|
| VPS `.env` | `CURSOR_API_KEY=crsr_...` |
| VPS `.env` | `CURSOR_REPO_URL=https://github.com/takuraanigatsuki-hub/AI_team_takura` |

---

## Шаг 7 — Telegram (опционально)

| Где | @BotFather в Telegram → `/newbot` |
|-----|-----------------------------------|
| VPS `.env` | `TELEGRAM_BOT_TOKEN` |
| VPS `.env` | `TELEGRAM_CHAT_ID` (ваш chat id) |

---

## Шаг 8 — Бэкапы (не потерять data/)

**На VPS**, cron:
```bash
crontab -e
# каждый день в 3:00
0 3 * * * cd /root/AI_team_takura && bash scripts/backup-data.sh >> backups/cron.log 2>&1
```

Архивы: `~/AI_team_takura/backups/ai-team-backup-*.tar.gz`

**Облако (опционально):** `rclone config` → в `.env` добавить `RCLONE_REMOTE=gdrive:AI_team_backups`

**`.env` с VPS** — сохраните копию в Bitwarden / 1Password (не в Git!).

---

## Быстрая таблица «куда что»

| Что | Где настраивается | Файл / место |
|-----|-------------------|--------------|
| Домен → сервер | DNS регистратор | A-запись → IP VPS |
| HTTPS | VPS Docker | `APP_DOMAIN` в `.env` + Caddy |
| LLM ключ | Smart AIPI / OpenAI | VPS `.env` |
| Admin вход | VPS один раз | `create_owner.py` |
| Код проекта | GitHub | push с ПК |
| Auto-update сервера | GitHub Secrets | `VPS_*` secrets |
| Пользователи, задачи | VPS диск | `data/` (бэкап!) |
| Figma | figma.com OAuth | VPS `.env` |
| Cursor | cursor.com API | VPS `.env` |

---

## Проверка что всё подключено

```bash
# на VPS
curl -s https://room.ВАШ-ДОМЕН.ru/api/health
# → {"ok":true,"service":"ai-team-room"}

docker compose -f docker-compose.prod.yml ps
# все сервисы Up
```

В браузере: **https://room.ВАШ-ДОМЕН.ru/app** → вход → чат, агенты, Inbox.

---

## Локально (ПК) vs Production (VPS)

| | ПК (разработка) | VPS (production) |
|--|-----------------|------------------|
| Запуск | `run.bat` | Docker на сервере |
| `.env` | свой локальный | **отдельный** на VPS |
| URL | localhost:8000 | https://домен/app |
| Данные | `data/` на ПК | `data/` на VPS + backup |
| После перезагрузки ПК | локальное может пропасть | **сервер работает 24/7** |

Подробный деплой: [DEPLOY.md](./DEPLOY.md)
