# REG.RU VPS — установка AI Team Room (Ubuntu)

Пошагово для сервера **Ubuntu 26.04 LTS** на REG.RU.

---

## Что понадобится

| Откуда | Что |
|--------|-----|
| Письмо / панель REG.RU | **IP сервера**, пароль **root** (или SSH-ключ) |
| Smart AIPI | `OPENAI_API_KEY` |
| Ваш ПК | PowerShell или PuTTY |

---

## Шаг 1 — Подключиться по SSH (с Windows)

### PowerShell

```powershell
ssh root@ВАШ_IP
```

Пример: `ssh root@185.123.45.67`

- При первом подключении: `yes`
- Пароль — из письма REG.RU («Доступ к серверу») или из панели **VPS → Доступ**

### Если SSH не пускает

1. REG.RU → **VPS → ваш сервер → Сеть / Firewall**  
   Открыть порты: **22**, **80**, **443**, **8000** (для первого запуска без домена)
2. Проверьте, что сервер **запущен** (не «выключен» в панели)

---

## Шаг 2 — Установка на сервере (один раз)

Скопируйте блок целиком в SSH-сессию:

```bash
apt-get update -qq
apt-get install -y git curl

git clone https://github.com/takuraanigatsuki-hub/AI_team_takura.git
cd AI_team_takura

bash scripts/install-server.sh
```

Если после Docker пишет про группу `docker`:

```bash
newgrp docker
cd ~/AI_team_takura
```

---

## Шаг 3 — Настроить `.env`

```bash
cd ~/AI_team_takura
cp .env.production.example .env
nano .env
```

### Минимум для старта (без домена)

```env
APP_DOMAIN=localhost

OPENAI_API_KEY=sk-ваш_ключ_из_smartaipi
OPENAI_BASE_URL=https://api.smartaipi.com/v1
LLM_MODEL=gpt-5.4-mini

POSTGRES_PASSWORD=ПридумайтеДлинныйПароль123!
DATABASE_URL=postgresql://aiteam:ПридумайтеДлинныйПароль123!@postgres:5432/aiteam

OUTBOUND_PROXY_MODE=off
OUTBOUND_PROXY=
```

Сохранить в nano: **Ctrl+O** → Enter → **Ctrl+X**

> Скопируйте `OPENAI_API_KEY` с вашего ПК из локального `.env`, если он уже работает.

---

## Шаг 4 — Запуск проекта

### Вариант A — быстрый старт по IP (без домена)

```bash
cd ~/AI_team_takura
docker compose up -d --build
```

Откройте в браузере:

```
http://ВАШ_IP:8000/app
```

### Вариант B — с доменом и HTTPS

1. REG.RU → **Домены → DNS** → A-запись `@` или `room` → **IP VPS**
2. В `.env`:
   ```env
   APP_DOMAIN=room.ваш-домен.ru
   FIGMA_REDIRECT_URI=https://room.ваш-домен.ru/api/figma/callback
   ```
3. Запуск:
   ```bash
   bash scripts/deploy-vps.sh
   ```
4. Сайт: `https://room.ваш-домен.ru/app`

---

## Шаг 5 — Создать admin (владельца)

```bash
cd ~/AI_team_takura
docker compose exec ai-team-room python scripts/create_owner.py
```

Следуйте подсказкам (email и пароль для входа).

---

## Шаг 6 — Проверка

```bash
docker compose ps
curl -s http://127.0.0.1:8000/api/health
```

Должно быть: `{"ok":true,"service":"ai-team-room"}`

---

## Управление с ПК (Cursor)

### Обновить код на сервере вручную

На сервере:

```bash
cd ~/AI_team_takura
bash scripts/deploy-vps.sh
```

### Или с ПК через GitHub

```powershell
cd C:\Users\USER\Desktop\AI_team_takura-main
.\scripts\deploy-from-pc.ps1 -Message "update"
```

Auto-deploy: GitHub → Settings → Secrets → `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`  
(см. [WHERE_TO_CONNECT.md](./WHERE_TO_CONNECT.md))

---

## Полезные команды на REG.RU VPS

```bash
# логи
docker compose logs -f ai-team-room

# перезапуск
cd ~/AI_team_takura && docker compose restart

# остановить
docker compose down

# бэкап data/
bash scripts/backup-data.sh
```

---

## Частые проблемы REG.RU

| Проблема | Решение |
|----------|---------|
| Сайт не открывается | Firewall REG.RU: порты 8000 или 80/443 |
| `permission denied` docker | `newgrp docker` или `sudo docker compose ...` |
| LLM не отвечает | Проверить `OPENAI_API_KEY` в `.env`, перезапуск |
| HTTPS не работает | Нужен домен + A-запись на IP, не голый IP |

---

## Схема

```
ПК (Cursor)  --ssh-->  REG.RU VPS (Ubuntu 26.04)
                           └── ~/AI_team_takura
                                 ├── .env
                                 ├── data/      ← пользователи, задачи
                                 └── Docker     ← app :8000

Браузер  -->  http://IP:8000/app   (без домена)
           или https://room.домен.ru/app
```
