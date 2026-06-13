# Деплой AI Team Room на VPS (24/7)

Код — в **GitHub**, данные — на **сервере**, управление — из **Cursor** на ПК.

## Архитектура

```
Cursor (ПК)  →  git push  →  GitHub  →  SSH deploy  →  VPS (Docker)
                                                          ├── data/
                                                          ├── output/
                                                          └── knowledge/
```

Локальный `run.bat` нужен только для разработки. Production живёт на VPS.

---

## 1. Аренда VPS

- Ubuntu 22.04+, 2 GB RAM, 20 GB SSD
- Провайдеры: Timeweb, Hetzner, DigitalOcean
- Откройте порты **80** и **443** (и **22** для SSH)

## 2. Первичная установка на сервере

```bash
ssh root@ВАШ_IP

# один раз
git clone https://github.com/takuraanigatsuki-hub/AI_team_takura.git
cd AI_team_takura
bash scripts/install-server.sh

nano .env   # ключи + домен
bash scripts/deploy-vps.sh
```

### Важные переменные в `.env`

| Переменная | Пример | Зачем |
|------------|--------|-------|
| `APP_DOMAIN` | `room.example.com` | HTTPS через Caddy |
| `OPENAI_API_KEY` | `sk-...` | LLM агентов |
| `POSTGRES_PASSWORD` | случайная строка | БД (не `aiteam` в prod) |
| `FIGMA_REDIRECT_URI` | `https://room.example.com/api/figma/callback` | OAuth Figma |

DNS: A-запись домена → IP сервера.

После деплоя: **https://ВАШ_ДОМЕН/app**

### Создать owner (admin)

```bash
docker compose -f docker-compose.prod.yml exec ai-team-room python scripts/create_owner.py
```

---

## 3. Управление из Cursor (ПК)

```powershell
git add .
git commit -m "feat: ..."
git push origin main
```

С **auto-deploy** (шаг 4) сервер обновится сам.

Без auto-deploy — на сервере:

```bash
cd ~/AI_team_takura && bash scripts/deploy-vps.sh
```

---

## 4. Auto-deploy (GitHub Actions)

В репозитории: **Settings → Secrets and variables → Actions**

| Secret | Значение |
|--------|----------|
| `VPS_HOST` | IP или домен сервера |
| `VPS_USER` | `root` или `deploy` |
| `VPS_SSH_KEY` | приватный SSH-ключ (полностью) |
| `VPS_PATH` | `/root/AI_team_takura` (опционально) |
| `VPS_PORT` | `22` (опционально) |

На сервере добавьте публичный ключ в `~/.ssh/authorized_keys`.

При каждом `push` в `main` workflow `.github/workflows/deploy.yml` выполнит `deploy-vps.sh`.

---

## 5. Резервные копии

```bash
# вручную
bash scripts/backup-data.sh

# cron — каждый день в 3:00
crontab -e
# 0 3 * * * cd ~/AI_team_takura && bash scripts/backup-data.sh >> backups/cron.log 2>&1
```

Архивы: `backups/ai-team-backup-YYYYMMDD-HHMMSS.tar.gz` (хранятся 14 последних).

### Облако (опционально)

```bash
# rclone config → remote "gdrive:"
export RCLONE_REMOTE="gdrive:AI_team_backups"
bash scripts/backup-data.sh
```

### Восстановление

```bash
bash scripts/restore-data.sh backups/ai-team-backup-20260613-030000.tar.gz
bash scripts/deploy-vps.sh
```

---

## 6. Что хранить отдельно (не в Git)

| Файл | Где backup |
|------|------------|
| `.env` | менеджер паролей + копия на сервере |
| `data/` | `backup-data.sh` + облако |
| SSH-ключи | локально + GitHub Secrets |

**Никогда не коммитьте `.env`** — он в `.gitignore`.

---

## 7. Локальная разработка vs production

| | Локально | VPS |
|--|----------|-----|
| Запуск | `run.bat` | `docker compose -f docker-compose.prod.yml up -d` |
| URL | localhost:8000 | https://домен/app |
| Данные | `data/` на ПК | `data/` на сервере |
| Перезагрузка ПК | всё локальное пропадает* | сервер работает 24/7 |

\*если не делаете push и backup

---

## 8. Проверка

```bash
docker compose -f docker-compose.prod.yml ps
curl -s https://ВАШ_ДОМЕН/api/health
```

Логи:

```bash
docker compose -f docker-compose.prod.yml logs -f ai-team-room
```
