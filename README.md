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

## 🎲 Расширенный самообучающийся слой (bandit + GA + online sentiment + retirement)

Поверх адаптивного слоя добавлены ещё 4 механизма:

### 1. Thompson Sampling bandit (`app/adaptive/bandit.py`)
Каждая стратегия моделируется как **Beta(α, β)** распределение вероятности
«правильного» голоса. При каждом успехе (голос совпал с финальным сигналом и
последующая сделка была прибыльной) → α += 1. При неудаче → β += 1.
На каждом тике sample из Beta даёт принципиальный explore/exploit:
новые стратегии (мало samples → широкое распределение) получают шанс,
устоявшиеся проигрывающие — почти всегда низкий вес.
Bandit-веса блендятся с adaptive (по умолчанию 50/50 через `BANDIT_BLEND`).

### 2. Genetic algorithm (`app/adaptive/genetic.py`)
Поверх результатов auto-tuner: берёт top-N родителей, делает crossover
(параметр от A, B или интерполяция) + мутацию (±20% от диапазона) →
популяция 12 особей → бэктест → top-K выживших → следующее поколение.
2 поколения по умолчанию. Лучшие сохраняются как
`StrategyConfig(created_by='ga')`. Это локальный поиск вокруг островков
хорошего score, найденных random search'ем tuner'а.

### 3. Online sentiment learning (`app/sentiment/online.py`)
Лексикон **обучается на реакции цены**. Каждые 6 часов:
1. Берём новости за окно [T - 8h, T].
2. Для каждой новости считаем последующее % изменение цены упомянутого
   инструмента за 8 часов.
3. Для каждого нестоп-слова в новости обновляем средневзвешенный
   score через SGD-правило `w ← w + lr · scale · (price_change - w)`,
   где scale = 1/√(samples+1) (новые слова обновляются сильнее).
4. Сохраняем в `online_lexicon`.

`combined_score(text)` = 0.7 × static lexicon + 0.3 × online learned —
агент использует это как обогащённый сентимент.

### 4. Strategy retirement (`app/adaptive/retirement.py`)
Каждые 6 часов: если стратегия `created_by ∈ {tuner, llm, ga}` имела
≥ 30 решений и её `attributable_pnl < -3%` за окно — она автоматически
выключается. **User-стратегии не трогаются никогда** (защищённые).
Это предохраняет портфель от роста «галлюцинаций» tuner'а или LLM.

### Новые эндпоинты адаптивного слоя
- `GET  /api/adaptive/bandit` — постериоры α, β + sample weights
- `POST /api/adaptive/bandit/update?lookback=500` — обновить из истории
- `POST /api/adaptive/genetic/run` — запустить GA вручную
- `POST /api/adaptive/retirement/run` — выгнать убыточных
- `POST /api/adaptive/sentiment/learn` — один цикл обучения лексикона
- `GET  /api/adaptive/sentiment/lexicon?min_samples=2` — посмотреть выученное

### Жёсткие safety-гарантии (продолжают действовать)
- Bandit + GA **никогда не выходят за допустимые диапазоны параметров** —
  `clamp_params()` принудителен.
- GA **никогда не создаёт новых базовых стратегий** — только мутации
  существующих.
- Online sentiment **обновляет ТОЛЬКО веса слов**, не лезет в торговую логику.
- Retirement **никогда не отключает user-конфиги** — даже если они в минусе.

## 🧬 Адаптивный слой: бот учится на ошибках и сам генерирует стратегии

Поверх всего предыдущего поднят **автономный цикл самообучения**:

1. **Адаптивные веса стратегий**
   Каждый час `compute_performance_snapshots` пробегает по последним
   `ADAPTIVE_LOOKBACK_DECISIONS=500` решениям + закрытым сделкам, считает
   per-strategy attributable PnL (по доле confidence в финальном сигнале),
   accuracy и applies экспоненциальное переvзвешивание
   `w = exp(λ · z_score(pnl) + accuracy_bonus)`. Веса умножаются на
   confidence каждого голоса в агрегаторе — выигрывающие стратегии
   получают больший вес, проигрывающие — меньший.

2. **Регим-детектор** (`app/adaptive/regime.py`)
   Классифицирует рынок как `trending_up / trending_down / ranging / volatile`
   на основе наклона log-цены и z-score реализованной волатильности
   относительно baseline'а (вычисляется СТРОГО ИЗ ИСТОРИИ ДО текущего
   окна, чтобы спайк не «растворялся» в собственном baseline).
   В режиме `trending` бустит трендовые стратегии (MA, BB), в `ranging`
   — mean-reversion (RSI), в `volatile` — режет всех.

3. **Auto-tuner** (`app/adaptive/tuner.py`)
   Раз в `TUNER_INTERVAL_HOURS=24` часов делает walk-forward random-search
   по параметрам каждой базовой стратегии: 30 случайных конфигов на
   каждую базу, 3 фолда исторических OHLCV, score = средний PnL%
   out-of-sample. Лучшие `TUNER_KEEP_TOP_N=2` сохраняются как
   `StrategyConfig(created_by='tuner')` и автоматически подхватываются
   в активный набор через `engine.reload_strategies_from_db()`.

4. **LLM strategy proposer** (`app/adaptive/proposer.py`)
   Раз в `PROPOSER_INTERVAL_HOURS=24` LLM получает на вход:
   допустимые диапазоны параметров, текущие активные стратегии + их
   adaptive weights, performance snapshots, memos агента. Возвращает
   JSON со списком новых конфигов. **Никакого кода — только числа**:
   модель может предложить лишь параметры существующих базовых
   стратегий (`ma_crossover`, `rsi_reversion`, `bollinger_breakout`),
   и они автоматически clamp-аются под допустимые диапазоны. Каждое
   предложение проходит микро-бэктест против baseline дефолта;
   принимаются только те, у которых positive PnL.

5. **Параметризуемый strategy registry**
   `STRATEGY_FACTORIES` + `DynamicStrategy` — стратегии теперь живут
   как `StrategyConfig` в БД (имя, база, JSON-параметры, score,
   created_by). При каждом тике engine может перезагрузить их из
   БД (`/api/adaptive/strategies/reload` или авто-цикл).

### Новые эндпоинты адаптивного слоя
- `GET  /api/adaptive/weights` — текущие веса + per-strategy snapshots
- `POST /api/adaptive/weights/refresh` — пересчитать прямо сейчас
- `GET  /api/adaptive/regime?symbol=BTC/USDT` — текущий регим рынка
- `GET  /api/adaptive/strategies` — все конфиги в БД
- `POST /api/adaptive/strategies/{id}/toggle` — включить/выключить
- `POST /api/adaptive/strategies/reload` — engine перечитывает БД
- `POST /api/adaptive/tuner/run?samples=20` — запустить тюнер
- `POST /api/adaptive/proposer/run` — запустить LLM-proposer
- `GET  /api/adaptive/performance_history` — история снапшотов

### Жёсткие safety-гарантии (важно)
- **LLM-proposer не может выйти за диапазон параметров** — `clamp_params()`
  принудительно приводит к допустимым значениям + типам.
- **LLM-proposer не может предложить новую базовую стратегию** — только
  параметры существующих (`ma_crossover` / `rsi_reversion` / `bollinger_breakout`).
- **Никакой исполняемый код в БД не хранится** — только JSON параметров.
- **Каждое LLM-предложение проходит бэктест перед активацией**.
- **Tuner результаты тоже проходят walk-forward** — score выше baseline'а
  не означает «работать в live», но это минимальный фильтр.

### Что видит UI
На дашборде появилась карточка «🧬 Активные стратегии + адаптивные веса»:
- регим рынка с confidence,
- список активных стратегий с их именем, базой, `[created_by]` меткой
  (`user|tuner|llm`), adaptive weight, effective weight (после regime
  preferences), backtest score,
- кнопки «Tuner», «LLM proposer», «Reload».

## 🆙 Что добавлено в последнем апдейте (топовая модель + tools + reflection + factors + MC)

- **Топовая reasoning-модель по умолчанию** (`LLM_MODEL=gpt-5.4-high`) +
  пресеты для Anthropic через OpenRouter (`anthropic/claude-opus-4.8`) и
  локального инференса (`LLM_BASE_URL=http://localhost:11434/v1`).
- **Native function-calling** (OpenAI tools API) для агента — строгая
  валидация схемы, symbol enum жёстко ограничен `allowed_symbols`.
  Автоматический fallback в JSON-mode на моделях без поддержки tools.
- **Reflection-цикл**: раз в `REFLECTION_INTERVAL_HOURS` часов агент
  перечитывает свой дневник + закрытые сделки, формирует JSON
  `{summary, rules_learned[]}` и сохраняет в таблицу `agent_memos`.
  Memo подмешивается в контекст следующих циклов — простейшая форма
  «обучения без ML».
- **Multi-factor decomposition** (`app/analytics/factors.py`):
  кросс-секционная OLS — BTC β, ETH β (резидуал), momentum, volatility,
  size proxy, alpha, R² для каждого актива + взвешенные портфельные
  экспозиции и `diversification_score` (нормированный 1 - HHI).
- **Monte Carlo VaR** (`app/analytics/monte_carlo.py`): N симуляций из
  multivariate normal на ковариации фактических доходностей, для
  настраиваемого горизонта и α. На дашборде идёт рядом с historical VaR.

Новые эндпоинты: `GET /api/agent/memos`, `POST /api/agent/reflect`,
`GET /api/analytics/monte_carlo`, `GET /api/analytics/factors`.

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
