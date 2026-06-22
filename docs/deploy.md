# Деплой Trade в облако

> ⚠️ Перед запуском в облаке **обязательно** установите `WEB_USER` / `WEB_PASSWORD`
> в переменных окружения — иначе ваш дашборд окажется в открытом доступе.

Если режим `live`, дополнительно:
- API-ключи биржи **с правом trade, без withdraw**, с привязкой к IP.
- Меньший `RISK_PER_TRADE`, более жёсткий `DAILY_LOSS_LIMIT_PCT`.
- Включённые Telegram-уведомления — чтобы ловить аномалии сразу.

---

## Вариант 1: Fly.io (рекомендую — самый простой, ~$5/мес)

Fly даёт persistent volume для SQLite, healthcheck, авто-перезапуск, бесплатный TLS.

```bash
# один раз:
brew install flyctl       # или curl -L https://fly.io/install.sh | sh
fly auth login

cd path/to/trade
fly launch --no-deploy --copy-config       # подхватит fly.toml; имя приложения подтвердите
fly volumes create trade_data --size 1     # 1 ГБ; на $0.15/мес

# секреты (LLM, Telegram, биржа — что используете):
fly secrets set \
  LLM_API_KEY=sk-... \
  TELEGRAM_BOT_TOKEN=123:abc... \
  TELEGRAM_CHAT_ID=12345678 \
  WEB_USER=admin \
  WEB_PASSWORD=$(openssl rand -base64 24)
# для live:
fly secrets set \
  MODE=live \
  EXCHANGE_API_KEY=... \
  EXCHANGE_API_SECRET=...

fly deploy
fly status
fly logs -f
```

Открыть дашборд: `https://<app-name>.fly.dev`.
Обновление: после `git push` локально → `fly deploy`.
Откат: `fly releases` → `fly releases revert <N>`.

---

## Вариант 2: Любой VPS (Hetzner / DigitalOcean / Linode, от $4/мес)

На свежей Ubuntu 22.04/24.04:

```bash
# 0. ssh root@your-vps
adduser trade && usermod -aG sudo trade
su - trade

# 1. зависимости
sudo apt update && sudo apt install -y python3.12 python3.12-venv git nginx certbot python3-certbot-nginx ufw

# 2. клонируем
git clone https://github.com/<you>/<trade-repo>.git /home/trade/app
cd /home/trade/app
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. конфиг
cp .env.example .env
nano .env       # вписать LLM_API_KEY, TELEGRAM_*, WEB_USER, WEB_PASSWORD…

# 4. systemd-юнит (см. ниже trade.service)
sudo cp deploy/trade.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now trade
sudo systemctl status trade

# 5. nginx + HTTPS
sudo cp deploy/nginx-trade.conf /etc/nginx/sites-available/trade
sudo ln -s /etc/nginx/sites-available/trade /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d trade.example.com   # автоматический TLS

# 6. firewall
sudo ufw allow 22 && sudo ufw allow 80 && sudo ufw allow 443 && sudo ufw enable
```

Файлы `trade.service` и `nginx-trade.conf` лежат в [`deploy/`](../deploy/).

Обновление: `cd /home/trade/app && git pull && sudo systemctl restart trade`.

---

## Вариант 3: Docker / docker-compose на любом сервере

```bash
git clone ... trade && cd trade
cp .env.example .env && nano .env
docker compose up -d --build
docker compose logs -f
# обновление:
git pull && docker compose up -d --build
```

Для прода поставьте перед контейнером Caddy/Traefik с автоматическим TLS,
либо примонтируйте reverse-proxy.

---

## Вариант 4: Railway / Render

В корне уже есть `Procfile` (`web: python run.py`). На обоих платформах:

1. Создайте проект из вашего GitHub-репозитория.
2. В Environment vars впишите всё из `.env.example` (что используете).
3. Persistent storage:
   - **Railway:** добавьте volume и смонтируйте в `/data`,
     в `DATABASE_URL` укажите `sqlite:////data/trade.db`.
   - **Render:** используйте persistent disk, та же логика.
4. Билд автоматический из `requirements.txt` (Python buildpack).

---

## Что мониторить в проде

| Источник | Что смотреть | Action |
| --- | --- | --- |
| `/health` | 200 OK | поднять upmoonitoring-проверку (UptimeRobot / Better Stack) |
| `/api/bot/status` | `running=true`, `last_tick_at` свежий | если последний тик > 5 мин — alert |
| Telegram-бот | приходят дневные сводки и сообщения об ошибках | если тихо > сутки — что-то отвалилось |
| `data/trade.db` | размер не растёт катастрофически | при необходимости настроить ротацию старых равенств |
| Лог приложения | `ERROR`/`WARNING` | централизованный лог (Loki/ELK) для прода |

---

## Что нужно мне (агенту), чтобы помочь с деплоем

Сам задеплоить за вас я **не могу** — у меня нет ваших облачных аккаунтов и
платёжных данных. Но если приклеите вывод первой команды (`fly launch …`
или `docker compose up`), я разберу ошибки и подскажу следующие шаги.
