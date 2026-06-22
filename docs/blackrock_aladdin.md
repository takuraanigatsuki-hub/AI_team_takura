# Как устроен BlackRock Aladdin — и что из этого реализовано в Trade

> Краткий разбор того, как реально работает «ИИ BlackRock», и какие части
> этой архитектуры мы воспроизвели в этом проекте.

## Что такое Aladdin

**Aladdin** (Asset, Liability, Debt and Derivative Investment Network) — это
**платформа управления рисками и портфельной аналитики**, которую BlackRock
разрабатывает с 1988 года. Через неё проходит более **$21 триллиона** активов
(собственные деньги BlackRock + клиенты, которые лицензируют платформу:
Vanguard, государственные пенсионные фонды, страховые компании, ЦБ).

**Что Aladdin НЕ делает:**
- Не «угадывает» цены акций или биткоина.
- Не торгует high-frequency.
- Не заменяет портфельных менеджеров.

**Что Aladdin делает:**
1. **Считает риск** для каждой позиции, портфеля и фонда в реальном времени.
2. **Декомпозирует доходность** на систематические факторы (Barra-style models).
3. **Прогоняет стресс-тесты** на исторических и гипотетических сценариях.
4. **Оптимизирует портфели** под целевую функцию (Sharpe, риск-паритет, минимум tracking error к индексу).
5. **Мониторит ликвидность** — сколько дней нужно, чтобы выйти из позиции без сильного движения цены.
6. **Прикручивает NLP** к 10-K, earnings calls, новостям (через AI Labs, относительно недавно).

## Систематический подход BlackRock к выбору активов

Подразделение, которое реально занимается «стоковым пикингом», называется
**Systematic Active Equity (SAE)** — около $200 млрд под управлением,
основано на работах Энди Анга и команды. Их подход:

1. **Фактор-модели:** доходность раскладывается на 5–10 классических факторов
   (value, momentum, quality, low-vol, size) и десятки нишевых (sentiment,
   short interest, accruals, earnings surprise…).
2. **Альтернативные данные:**
   - спутниковые снимки парковок Walmart → предсказание выручки;
   - агрегированные транзакции по картам → оценка спроса в розничном секторе;
   - анализ patenting активности;
   - анализ NLP earnings-call transcript для извлечения тональности менеджмента.
3. **Ансамбли ML-моделей** (gradient boosting, random forest) для скоринга
   тысяч акций.
4. **Жёсткий риск-оверлей:** даже самая сильная alpha-идея режется
   риск-менеджером (tracking error к benchmark, концентрация по секторам,
   factor exposure constraints).

**Важно:** SAE в долгую обгоняет S&P 500 на **0.5–2% годовых**. Это много для
индустрии, но не «магия». Главная их сила — **дисциплина** и
**риск-контроль**, а не точность прогнозов.

## Что мы воспроизвели в Trade

Aladdin за $5+ млрд инфраструктуры мы повторить не можем. Но
концептуальную архитектуру — да, в модулях `app/analytics/`,
`app/optimizer/`, `app/sentiment/`:

### `app/analytics/risk.py`
- **Annualized μ, σ, Sharpe** портфеля по дневным/часовым доходностям.
- **Historical VaR** на уровне α (по умолчанию 95%) — α-перцентиль
  распределения доходностей.
- **CVaR (Expected Shortfall)** — среднее в хвосте за VaR.
- **Correlation matrix** между активами.
- **Beta к BTC** — стандартный β = Cov(r_i, r_BTC)/Var(r_BTC).
  В крипте BTC де-факто играет роль market portfolio.
- **Risk contribution** (marginal + component + % of total) — кто из позиций
  реально таскает на себе риск портфеля. Это **главная метрика Aladdin**:
  можно иметь только 20% денег в одном активе, но 80% риска.

### `app/analytics/stress.py`
Готовый набор реальных эпизодов:
- **covid_march_2020** — BTC -50% за 2 дня (13 марта 2020).
- **luna_collapse_may_2022** — обвал Terra/Luna.
- **ftx_nov_2022** — крах FTX, ноябрь 2022.
- **btc_flash_crash_30** — гипотетический BTC -30% за час, корреляции альтов 1.3×.
- **exchange_hack** — взлом крупной биржи.
- **regulation_ban_us** — гипотетический запрет в США.

Под каждый сценарий считается реальный долларовый удар по портфелю.

### `app/optimizer/`
- **`max_sharpe`** — Modern Portfolio Theory: максимизация Sharpe через
  scipy SLSQP с констрейнтами `sum(w)=1, w_i ∈ [w_min, w_max]`.
- **`min_variance`** — глобальный минимум дисперсии (Markowitz, 1952).
- **`risk_parity`** — каждый актив вносит **одинаковый риск** в портфель
  (подход Bridgewater All-Weather). Решается через scipy SLSQP по
  квадратичной функции отклонений от целевых contributions.

Все три выдают **рекомендуемые веса**, которые видит и LLM-агент, и
вы — на дашборде. Сравните их с тем, что у вас сейчас в портфеле — и
поймёте, на что *рекомендует* классическая теория.

### `app/sentiment/analyzer.py`
- **Лексикон**, заточенный под крипту: 30+ bullish-слов (`rally`, `surge`,
  `ETF approval`, `ATH`, `inflows`, …) и 40+ bearish (`hack`, `SEC`,
  `lawsuit`, `delisting`, `liquidations`, `rug pull`, …).
- **Aggregation per-symbol**: каждой новости проставляется sentiment
  score ∈ [-1, +1], затем фильтруем по упоминаниям ключевых слов
  (`bitcoin`/`btc`, `ethereum`/`eth`, …) и усредняем.
- **Возрастной фильтр** — выкидываем новости старше N часов.

Без LLM-ключа работает на лексиконе. С LLM-ключом стратегия `llm_advisor`
уже подключена к более «глубокому» анализу через GPT/Claude.

### Что видит LLM-агент

В каждый цикл агент получает (`app/agent/loop.py::_collect_snapshot`):
- portfolio snapshot (cash, equity, positions);
- индикаторы по каждому символу (EMA/RSI/Bollinger);
- **полную риск-картину**: σ, Sharpe, VaR, CVaR, β-к-BTC, contributions;
- **stress-test результаты** по портфелю;
- **предложения двух оптимизаторов** (max-Sharpe, risk-parity);
- **агрегированный sentiment** по каждому инструменту;
- свежие новости;
- собственный дневник предыдущих циклов.

Системный промпт явно требует: **обоснование любого действия должно ссылаться
на конкретные числа** (VaR, β, contribution, sentiment) и согласовываться с
оптимизаторами; если идёт против обоих — нужна очень веская причина.

## Чего у нас нет (и стоит ли это добавлять)

| Возможность Aladdin | Есть у нас? | Что бы потребовалось добавить |
|---|---|---|
| Factor models (Barra-style) | **✅ Реализовано** (BTC β + ETH β + momentum + vol + size + α + R²) | Можно расширить до 10+ факторов и добавить on-chain |
| Monte Carlo VaR | **✅ Реализовано** (`app/analytics/monte_carlo.py`) | Сейчас multivariate normal; можно добавить t-распределение и copulas для лучших хвостов |
| Liquidity-aware sizing | Нет | Учёт средневзвешенного спреда + книги заявок |
| Alt data (satellite, on-chain) | Нет | Glassnode / Santiment API (платные) |
| Realtime risk-aware execution | Нет — рыночные ордера | Limit-orders с риск-overlay (отказ исполнения, если выйти за лимит) |
| Forward-looking factor exposures | Нет | Прогнозы β через rolling regression |

Любую из этих фич можно добавить отдельным модулем. Скажите — какую.

## Главный вывод

«ИИ BlackRock» — это **не магия предсказания цен**, а **дисциплина управления
риском**, помноженная на огромную инфраструктуру. Воспроизвести масштаб
нельзя, но **архитектуру** — да. Этот проект — рабочая, тестируемая,
прозрачная её модель: на каждом тике видно, **сколько риска вы реально
несёте**, что предлагает классическая теория, и почему LLM-агент решает
именно так, как решает.

## Источники

- BlackRock. «Aladdin: Risk Management Platform.» blackrock.com/aladdin
- Andrew Ang. *Asset Management: A Systematic Approach to Factor Investing.* Oxford University Press, 2014.
- Harry Markowitz. «Portfolio Selection.» *Journal of Finance*, 1952.
- Edward Qian. «Risk Parity Portfolios.» PanAgora Asset Management, 2005.
- Bridgewater Associates. «The All Weather Strategy.» 2012.
- Marcos López de Prado. *Advances in Financial Machine Learning.* Wiley, 2018.
- Public BlackRock SAE research papers (Andrew Ang et al., SSRN).
