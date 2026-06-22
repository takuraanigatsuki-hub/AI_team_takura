# Trade — автономный торговый ИИ-бот

Самостоятельный торговый бот с веб-дашбордом для крипторынка.
Подключается к любой бирже из [`ccxt`](https://github.com/ccxt/ccxt) (Binance, Bybit, OKX, Kraken, Coinbase и ещё ~100),
крутит набор стратегий, агрегирует их голоса консенсусом, держит риск-менеджмент,
ведёт аудит-лог решений и показывает всё это в реальном времени в браузере.

> ## ⚠️ Без иллюзий — прочитайте, прежде чем «закидывать деньги»
>
> - **Гарантированно зарабатывающих ботов не существует.** Алгоритмическая торговля
>   — это бизнес с положительным ожиданием только при правильно подобранных
>   стратегиях, тщательном бэктесте, риск-менеджменте и постоянном надзоре.
> - **Вы можете потерять весь депозит.** Особенно быстро — на плечах, фьючерсах,
>   неликвидных монетах, во время флеш-крэшей, при сбое сети или ошибке в стратегии.
> - **Этот проект — инженерный каркас, а не «грааль».** Включённые стратегии
>   (MA crossover, RSI mean-reversion, Bollinger breakout) — учебные. Любую из них
>   нужно бэктестить, тюнить и валидировать на ваших данных.
> - **По умолчанию работает в paper-режиме** (виртуальные деньги, реальные цены).
>   Это безопасно и подходит для проверки гипотез. Реальная торговля включается
>   ОСОЗНАННО переменной `MODE=live` и API-ключами биржи.
> - **API-ключи биржи создавайте с правом TRADE, без WITHDRAW**, желательно с
>   привязкой к IP. Никогда не публикуйте `.env`.

## Что внутри

```
app/
├── core/         # конфиг (pydantic-settings) + SQLAlchemy + логирование
├── models/       # ORM-модели + pydantic-схемы
├── exchange/     # абстракция биржи + paper + ccxt-обёртка (~100 бирж)
├── strategies/   # MA crossover, RSI mean-reversion, Bollinger breakout, LLM advisor
├── risk/         # риск-менеджер: лимиты, стопы, тейки, дневной DD
├── engine/       # async торговый движок + бэктестер + агрегатор сигналов
├── metrics/      # метрики работы: PnL, Sharpe, drawdown, win-rate, attribution
├── analytics/    # VaR, CVaR, β-к-BTC, correlation, contribution-to-risk, stress tests
├── optimizer/    # Markowitz max-Sharpe / min-variance + risk parity (scipy)
├── sentiment/    # крипто-лексикон + агрегация sentiment per-symbol
├── llm/          # тонкий клиент OpenAI-совместимого chat API
├── news/         # RSS-агрегатор крипто-новостей (без ключей)
├── agent/        # автономный LLM-портфельный менеджер (Project-Vend-style)
├── telegram/     # Bot API: уведомления (orders/agent/errors) + команды
├── api/          # REST: bot, market, strategies, agent, metrics, analytics
├── templates/    # дашборд (Jinja2)
└── static/       # CSS + JS (Chart.js по CDN)

scripts/
└── historical_backtest.py    # CLI: скачивает годы OHLCV, прогоняет все стратегии

docs/
├── research.md            # выжимка из академики — почему ретейл теряет, что работало
├── blackrock_aladdin.md   # как устроен Aladdin и что из него тут воспроизведено
└── deploy.md              # пошаговый деплой: Fly.io / VPS systemd / Docker / Railway

deploy/
├── trade.service       # systemd-юнит для VPS
└── nginx-trade.conf    # reverse-proxy + место под certbot TLS

tests/            # pytest-набор: индикаторы, paper-биржа, риск, стратегии, бэктест
```

## Быстрый старт (local)

```bash
git clone <repo> trade && cd trade
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# при желании отредактируйте symbols/strategies/риск-параметры

python run.py
```

Откройте http://localhost:8000 — увидите дашборд. По умолчанию режим **paper**,
$10 000 виртуальных USDT, инструменты `BTC/USDT, ETH/USDT, SOL/USDT`,
таймфрейм `15m`, биржа `binance` (только public-данные, ключи не нужны).

Нажмите **«Старт»** — бот начнёт цикл: каждые `LOOP_INTERVAL_SECONDS` секунд
он получает свечи, гоняет стратегии, агрегирует голоса, проверяет риск-менеджер
и (если решение позволено) выставляет виртуальные ордера.

## Docker

```bash
cp .env.example .env
docker compose up -d --build
# логи: docker compose logs -f
```

## Облачный деплой (24/7)

В корне есть `fly.toml` для Fly.io и `Procfile` для Railway/Render.
Подробные пошаговые инструкции (Fly.io / Hetzner-VPS + systemd / Docker /
Railway) — в [`docs/deploy.md`](docs/deploy.md).

Самый простой вариант (~$5/мес):

```bash
fly auth login
fly launch --no-deploy --copy-config
fly volumes create trade_data --size 1
fly secrets set LLM_API_KEY=... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
                WEB_USER=admin WEB_PASSWORD=$(openssl rand -base64 24)
fly deploy
```

## Telegram-бот

Если задать `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` в `.env`, бот будет:

- **присылать уведомления** о каждом ордере (paper или live), о действиях
  LLM-агента (тезис + список выполненных и отклонённых действий), об
  ошибках движка;
- **раз в сутки** в `TELEGRAM_DAILY_SUMMARY_HOUR_UTC` слать сводку:
  капитал, дневной P&L, режим;
- **принимать команды** (только из вашего chat_id):
  `/status` `/pnl` `/positions` `/orders` `/journal` `/pause` `/resume`
  `/kill` `/unkill` `/agent_start` `/agent_stop` `/agent_tick` `/help`.

Создать бота: напишите [@BotFather](https://t.me/BotFather) → `/newbot` →
получите токен. Узнать свой chat_id: напишите боту любое сообщение,
затем откройте `https://api.telegram.org/bot<TOKEN>/getUpdates`.

## Исторический бэктест на годах данных

Скрипт `scripts/historical_backtest.py` скачивает OHLCV из любой биржи ccxt
(Binance/Bybit/OKX/…) и прогоняет на нём каждую стратегию по отдельности,
ансамбль с консенсусом и buy-&-hold для сравнения:

```bash
python -m scripts.historical_backtest \
  --exchange binance \
  --symbols BTC/USDT,ETH/USDT,SOL/USDT \
  --timeframe 1h \
  --years 3 \
  --balance 10000
```

Результат — в `data/backtest_*.json` + сводка в `data/backtest_summary.json`.
Перед запуском бота на реальных деньгах **обязательно прогоните этот скрипт
и сравните с buy-&-hold**.

## 📊 Aladdin-style риск-аналитика и оптимизация портфеля

Поверх торгового движка работает слой портфельной аналитики и оптимизации,
конструктивно копирующий подход BlackRock Aladdin: **риск ПЕРВЫМ, доходность ВТОРОЙ**.

Что считается на каждый запрос:

- **Аналитика риска** (`/api/analytics/risk`):
  annualized μ/σ/Sharpe, **historical VaR + CVaR (95%)**, корреляции,
  **бета к BTC**, **risk contribution** (marginal + component + % of total) —
  какая позиция реально таскает на себе риск портфеля.
- **Стресс-тесты** (`/api/analytics/stress`) на реальных сценариях:
  COVID-март-2020, Terra/Luna, FTX, плюс гипотетические BTC -30% флеш-крэш,
  взлом биржи, регуляторный запрет в США.
- **Оптимизатор портфеля** (`/api/optimizer/{max_sharpe|min_variance|risk_parity}`):
  Markowitz max-Sharpe, минимум дисперсии и **risk-parity**
  (Bridgewater All-Weather style) через scipy SLSQP с констрейнтами.
- **Сентимент-анализ новостей** (`/api/sentiment`): крипто-лексикон
  (bullish: ETF approval, ATH, inflows; bearish: hack, SEC, delisting, …)
  с агрегацией per-symbol и фильтром по возрасту.

Всё это автоматически передаётся **LLM-агенту** в контекст: он получает не
голый снимок цен, а полную риск-картину + предложения двух оптимизаторов +
сентимент по каждому инструменту. Системный промпт требует обосновывать
любое действие конкретными числами (VaR, β, contribution, sentiment).

Дашборд показывает всё это в отдельной панели «Риск-аналитика»:
VaR/CVaR, β к BTC, contribution-to-risk, таблицу стресс-тестов и
рекомендуемые веса от обоих оптимизаторов.

Подробнее: [`docs/blackrock_aladdin.md`](docs/blackrock_aladdin.md) —
что такое Aladdin на самом деле, какие его части воспроизведены здесь и
чего сознательно нет.

## Research: почему ретейл-трейдеры теряют

Перед тем, как «нести деньги в бота», прочитайте [`docs/research.md`](docs/research.md)
— компактная выжимка из академических исследований (Barber & Odean, ESMA,
Chague et al., Lopez de Prado и др.) о реальной статистике ретейл-трейдинга:
~80% счетов в убытке, типичные причины (overtrading, отсутствие риск-менеджмента,
plечо, overfitting), и что исторически работало (momentum, mean-reversion,
диверсификация, простые правила вместо сложных ML).

## Переход на live (реальные деньги)

1. На бирже создайте API-ключи **с правом trade, без права withdraw**.
2. В `.env` укажите:
   ```env
   MODE=live
   EXCHANGE_ID=binance         # или bybit / okx / kraken / ...
   EXCHANGE_API_KEY=...
   EXCHANGE_API_SECRET=...
   EXCHANGE_API_PASSWORD=...   # bybit/okx требуют passphrase
   EXCHANGE_TESTNET=false      # или true для песочницы
   ```
3. Уменьшите `RISK_PER_TRADE`, `MAX_OPEN_POSITIONS`, поставьте более жёсткие
   `STOP_LOSS_PCT`, `DAILY_LOSS_LIMIT_PCT`.
4. Перезапустите. На дашборде должен загореться красный баннер **LIVE MODE**.
5. Имейте под рукой кнопку **KILL** — она блокирует открытие новых сделок.

## Бэктест

REST-эндпоинт:

```
POST /api/strategies/backtest?symbol_base=BTC&symbol_quote=USDT&timeframe=1h&limit=1000&starting_balance=10000
Content-Type: application/json
```

Можно указать конкретный набор стратегий через `?strategies=ma_crossover&strategies=rsi_reversion`.
Ответ содержит `final_equity`, `pnl`, `pnl_pct`, список сделок и equity-curve —
готово к построению графика.

## LLM-советник (опционально)

Если задать `LLM_API_KEY` в `.env`, стратегия `llm_advisor` будет передавать
снимок индикаторов (price, EMA, RSI, Bollinger) в LLM и получать структурированный
JSON-сигнал. Поддерживается OpenAI и OpenRouter (любой OpenAI-совместимый API).
Без ключа стратегия молча возвращает `hold`.

## 🤖 Автономный ИИ-агент (Project-Vend-style)

В дополнение к систематическим стратегиям проект включает **автономного
LLM-портфельного менеджера**. Он работает по таймеру (`AGENT_INTERVAL_SECONDS`),
самостоятельно собирает контекст и решает, что делать. На каждом цикле он видит:

- снимок портфеля (cash, equity, открытые позиции, дневной P&L);
- свежие OHLCV-свечи и технические индикаторы (EMA, RSI, Bollinger) по
  разрешённым инструментам;
- свежие крипто-новости из RSS-лент (CoinDesk, Cointelegraph, Decrypt,
  Bitcoin Magazine — без API-ключей);
- собственный «дневник» последних N циклов (`AGENT_JOURNAL_LOOKBACK`).

И возвращает структурированный JSON-план:

```json
{
  "thesis": "BTC консолидируется, RSI нейтральный, новостной фон спокойный",
  "actions": [
    {"tool": "place_order", "args": {"symbol":"BTC/USDT","side":"buy",
                                      "quote_amount":150,"reason":"..."}},
    {"tool": "hold", "args": {"reason":"ETH под сопротивлением, жду пробоя"}}
  ]
}
```

### Важно: жёсткие гарантии безопасности

- **Риск-менеджер — это veto.** Что бы ни попросил агент, его действие
  пропускается через `RiskManager`: размер позиции обрезается до
  `RISK_PER_TRADE * equity`, превышение `MAX_OPEN_POSITIONS` блокируется,
  достижение `DAILY_LOSS_LIMIT_PCT` блокирует новые покупки. Агент не может
  это обойти.
- **Allowlist символов.** Агент может торговать только инструментами из
  `SYMBOLS`. Попытка купить что-то ещё — отклоняется.
- **Лимит действий на цикл.** `AGENT_MAX_ACTIONS_PER_CYCLE` (по умолчанию 3) —
  предохранитель от «галлюцинации портфеля».
- **Аудит-лог.** Каждый цикл сохраняется в таблицу `agent_journal`:
  тезис → запрошенные действия → что реально исполнилось → ошибки. Видно в UI.

### Запуск

1. Получите ключ у OpenAI/OpenRouter (или поднимите локальный OpenAI-совместимый
   шлюз для Ollama/LM Studio).
2. В `.env`:
   ```env
   LLM_PROVIDER=openai            # или openrouter
   LLM_API_KEY=sk-...
   LLM_MODEL=gpt-4o-mini          # или другая модель с function/JSON-mode
   AGENT_ENABLED=true             # автостарт при запуске приложения
   AGENT_INTERVAL_SECONDS=600     # 10 минут между циклами — оптимум для 15m TF
   AGENT_MAX_ACTIONS_PER_CYCLE=3
   ```
3. `python run.py` — увидите в логах `AutonomousAgent started`.
4. В дашборде появится секция **🤖 Автономный ИИ-агент** с журналом мыслей,
   списком исполненных и отклонённых действий и кнопками **Старт / Tick / Стоп**.

### REST для агента

- `GET  /api/agent/status` — состояние, цикл, последний прогон, последняя ошибка
- `POST /api/agent/{start,stop,tick}` — управление
- `GET  /api/agent/journal?limit=30` — дневник
- `GET  /api/agent/news?limit=20&q=ETH` — текущие новости (со встроенным поиском)

### Что такое «Project Vend» и при чём он

В 2025 году Anthropic + Andon Labs провели эксперимент, где Claude месяц управлял
мини-бизнесом (автомат с напитками). Итог был [публично опубликован](https://www.anthropic.com/research/project-vend-1):
бот допустил серию забавных и поучительных ошибок (раздавал скидки, заказал
вольфрамовые кубики как товар, выдумывал встречи) и в итоге не вышел в прибыль.

Это честный сигнал: **долгая автономная агентность LLM — нерешённая задача**.
Поэтому в этом проекте агент работает в paper-режиме по умолчанию, под жёстким
риск-менеджером, с прозрачным дневником и кнопками **Pause / Stop / KILL**.

## Конфигурация — основные переменные

| Переменная | Что делает | Дефолт |
| --- | --- | --- |
| `MODE` | `paper` или `live` | `paper` |
| `EXCHANGE_ID` | id биржи в ccxt | `binance` |
| `SYMBOLS` | список через запятую | `BTC/USDT,ETH/USDT,SOL/USDT` |
| `TIMEFRAME` | `1m/5m/15m/1h/4h/1d` | `15m` |
| `STRATEGIES` | какие стратегии включены | `ma_crossover,rsi_reversion,bollinger_breakout` |
| `SIGNAL_CONSENSUS` | минимум согласных стратегий | `2` |
| `RISK_PER_TRADE` | доля капитала на одну сделку | `0.05` |
| `MAX_OPEN_POSITIONS` | макс. число позиций одновременно | `3` |
| `STOP_LOSS_PCT` / `TAKE_PROFIT_PCT` | защитные ордера | `0.03 / 0.06` |
| `DAILY_LOSS_LIMIT_PCT` | дневной кап на убыток | `0.05` |
| `WEB_USER` / `WEB_PASSWORD` | Basic Auth для дашборда | пусто |

Полный список — в `.env.example`.

## Тесты

```bash
pip install -r requirements.txt
pytest -q
```

Включают модульные тесты индикаторов, paper-биржи, риск-менеджера, стратегий,
агрегатора сигналов и бэктестера. Сетевые вызовы к биржам/LLM в тестах не выполняются.

## Что бы я улучшил перед серьёзными деньгами

1. **Walk-forward бэктест** и параметрическая оптимизация стратегий.
2. **Учёт slippage и комиссий точнее**, чем фиксированные 0.1%.
3. **Хеджирование/корзина инструментов** вместо одиночных монет.
4. **Алертинг** в Telegram/email на крупные движения и ошибки.
5. **Шифрование секретов** (например, через `sops`, AWS KMS).
6. **Мониторинг latency и состояния биржи** (отдельный health-проб).
7. **Trade journal** с разметкой «human override», чтобы потом обучать модели.

## Лицензия

MIT. Используете на свой страх и риск.
