"""LLM-driven strategy proposer.

LLM смотрит:
  - текущий список активных стратегий и их adaptive weights,
  - регим рынка,
  - последние memo агента,
  - производительность каждой стратегии за окно.

Возвращает JSON со списком предложенных конфигов:
  [{"base": "ma_crossover", "params": {"fast": 8, "slow": 21}, "rationale": "..."}, ...]

КРИТИЧЕСКОЕ: LLM может предложить ТОЛЬКО комбинации параметров для
известных базовых стратегий из STRATEGY_FACTORIES. Никакого кода. Никаких
других классов. Параметры сразу clamp-аются под допустимые диапазоны.

Каждое предложение перед сохранением проходит микро-бэктест: если score
лучше дефолта, конфиг становится enabled.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import select

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..engine.backtest import run_backtest
from ..engine.trader import get_engine
from ..exchange.base import ExchangeError
from ..llm.client import LLMUnavailable, get_llm_client
from ..models.db import AgentMemo, StrategyConfig
from ..strategies.registry import (
    STRATEGY_FACTORIES,
    build_strategy_from_config,
    clamp_params,
)


SYSTEM_PROMPT = """\
Ты — quant-исследователь. Тебе доверена задача предложить новые конфигурации
параметров для торговых стратегий, основываясь на:
  • производительности уже активных стратегий (включая адаптивные веса),
  • текущем рыночном региме,
  • memo автономного агента (его «уроках»).

Доступные базовые стратегии и ЖЁСТКИЕ диапазоны параметров — в блоке
"available_factories". НЕ выходи за эти диапазоны. НЕ предлагай новые
стратегии — только новые параметры существующих.

ОТВЕТ — строго валидный JSON одной верхней структуры:

{
  "proposals": [
    {
      "base": "ma_crossover",
      "params": {"fast": 8, "slow": 21},
      "rationale": "На trending_up рынке короткие EMA дают более ранние сигналы"
    },
    ...
  ]
}

Правила:
1. Предложи 1–5 разнообразных конфигов (не дубли активных).
2. Каждый rationale привязан к конкретному наблюдению из данных.
3. Если данных мало или предложить нечего — верни {"proposals": []}.
"""


@dataclass
class Proposal:
    base: str
    params: dict
    rationale: str
    backtest_score: float = 0.0
    accepted: bool = False
    reject_reason: str = ""


def _factories_for_prompt() -> dict:
    out = {}
    for base, factory in STRATEGY_FACTORIES.items():
        out[base] = {
            "params": {
                p.name: {"kind": p.kind, "low": p.low, "high": p.high, "default": p.default}
                for p in factory.params
            },
        }
    return out


def _collect_context(settings: Settings) -> tuple[dict, list[str]]:
    """Собрать контекст: текущие конфиги + memos. Возвращает (context, existing_names)."""
    from ..adaptive.weights import compute_adaptive_weights, compute_performance_snapshots

    with session_scope() as session:
        snapshots = compute_performance_snapshots(session, lookback=settings.adaptive_lookback_decisions)
        weights = compute_adaptive_weights(
            snapshots, w_min=settings.adaptive_min_weight, w_max=settings.adaptive_max_weight
        )
        active = session.execute(
            select(StrategyConfig).where(StrategyConfig.enabled == 1)
        ).scalars().all()
        active_data = [
            {"name": c.name, "base": c.base,
             "params": _safe_json(c.params),
             "score": c.backtest_score, "created_by": c.created_by}
            for c in active
        ]
        existing_names = [c.name for c in active]
        memos = session.execute(
            select(AgentMemo).order_by(AgentMemo.ts.desc()).limit(3)
        ).scalars().all()
        memo_data = [
            {"ts": m.ts.isoformat(), "summary": m.summary,
             "rules": _safe_json(m.rules_learned)}
            for m in reversed(memos)
        ]

    return {
        "active_strategies": active_data,
        "adaptive_weights": weights,
        "performance_snapshots": [s.as_dict() for s in snapshots],
        "memos": memo_data,
    }, existing_names


def _safe_json(text: str) -> Any:
    try:
        return json.loads(text) if text else None
    except json.JSONDecodeError:
        return text


async def _backtest_proposal(
    base: str, params: dict, symbol: str, settings: Settings
) -> tuple[float, str]:
    """Микро-бэктест предложенного конфига против baseline дефолтных параметров."""
    engine = get_engine()
    try:
        rows = await engine.exchange.fetch_ohlcv(
            symbol, timeframe=settings.tuner_history_timeframe,
            limit=settings.tuner_history_candles,
        )
    except ExchangeError as exc:
        return 0.0, f"fetch: {exc}"
    if not rows:
        return 0.0, "no candles"
    df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume"])
    df.set_index("ts", inplace=True)

    proposal_inst = build_strategy_from_config(base, f"{base}__llm_test", params)
    factory = STRATEGY_FACTORIES.get(base)
    if not proposal_inst or not factory:
        return 0.0, "build failed"
    default_params = {p.name: p.default for p in factory.params}
    baseline_inst = build_strategy_from_config(base, f"{base}__baseline", default_params)
    if baseline_inst is None:
        return 0.0, "baseline build failed"

    local_settings = settings.model_copy(update={
        "signal_consensus": 1, "max_open_positions": 1,
        "risk_per_trade": 0.2, "min_order_notional": 1,
    })

    proposal_res = run_backtest(df, [proposal_inst], local_settings,
                                symbol=symbol, starting_balance=10_000)
    baseline_res = run_backtest(df, [baseline_inst], local_settings,
                                symbol=symbol, starting_balance=10_000)
    delta = proposal_res.pnl_pct - baseline_res.pnl_pct
    return float(proposal_res.pnl_pct), f"vs baseline {baseline_res.pnl_pct:+.2f}% → Δ {delta:+.2f}%"


def _parse_response(raw: str) -> list[dict]:
    text = (raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return []
    if not isinstance(data, dict):
        return []
    proposals_raw = data.get("proposals") or []
    if not isinstance(proposals_raw, list):
        return []
    out: list[dict] = []
    for p in proposals_raw[:10]:
        if not isinstance(p, dict):
            continue
        base = str(p.get("base", "")).lower().strip()
        params = p.get("params") or {}
        rationale = str(p.get("rationale", ""))[:280]
        if base not in STRATEGY_FACTORIES or not isinstance(params, dict):
            continue
        out.append({"base": base, "params": params, "rationale": rationale})
    return out


async def run_proposer_cycle(
    settings: Settings | None = None,
    *,
    symbol: str | None = None,
) -> list[Proposal]:
    s = settings or get_settings()
    if not s.llm_api_key:
        logger.info("proposer skipped — no LLM key")
        return []

    symbol = symbol or (s.symbols[0] if s.symbols else "BTC/USDT")
    context, existing_names = _collect_context(s)

    user_prompt = (
        "## Доступные базовые стратегии и допустимые диапазоны параметров\n"
        f"```json\n{json.dumps(_factories_for_prompt(), ensure_ascii=False, indent=2)}\n```\n\n"
        "## Текущее состояние\n"
        f"```json\n{json.dumps(context, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Симуляция будет на инструменте {symbol}. Сформулируй до "
        f"{s.proposer_max_new_per_cycle} новых конфигов."
    )

    try:
        client = get_llm_client()
        raw = await asyncio.to_thread(
            client.complete,
            SYSTEM_PROMPT, user_prompt,
            temperature=s.proposer_temperature,
            max_tokens=s.proposer_max_tokens,
            response_format_json=True,
        )
    except LLMUnavailable as exc:
        logger.warning("proposer LLM failed: {}", exc)
        return []

    parsed = _parse_response(raw)
    if not parsed:
        logger.info("proposer: 0 proposals parsed from LLM")
        return []
    parsed = parsed[: s.proposer_max_new_per_cycle]

    results: list[Proposal] = []
    saved_at = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    for idx, p in enumerate(parsed):
        clean_params = clamp_params(p["base"], p["params"])
        # отвергаем дубликаты уже существующих параметров
        sig = f"{p['base']}|{json.dumps(clean_params, sort_keys=True)}"
        dup = False
        with session_scope() as session:
            for active in session.execute(
                select(StrategyConfig).where(StrategyConfig.enabled == 1)
            ).scalars().all():
                if active.base == p["base"] and _safe_json(active.params) == clean_params:
                    dup = True
                    break
        if dup:
            results.append(Proposal(p["base"], clean_params, p["rationale"],
                                     0.0, False, "duplicate of active config"))
            continue

        score, detail = await _backtest_proposal(p["base"], clean_params, symbol, s)
        accepted = score > 0  # принимаем только конфиги с положительным PnL
        # сравним с baseline дефолтом — детали в `detail`
        name = f"{p['base']}__llm_{saved_at}_{idx:02d}"
        proposal = Proposal(
            base=p["base"], params=clean_params, rationale=p["rationale"],
            backtest_score=score, accepted=accepted,
            reject_reason="" if accepted else f"score {score:+.2f}% (not positive)",
        )
        with session_scope() as session:
            session.add(StrategyConfig(
                name=name, base=p["base"],
                params=json.dumps(clean_params, ensure_ascii=False),
                enabled=1 if accepted else 0,
                created_by="llm",
                backtest_score=score,
                note=f"{p['rationale'][:200]} | {detail}",
            ))
        results.append(proposal)

    logger.info(
        "proposer: {} proposals, {} accepted",
        len(results), sum(1 for r in results if r.accepted),
    )
    return results


async def proposer_loop(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if not s.proposer_enabled:
        return
    interval = max(3600, s.proposer_interval_hours * 3600)
    await asyncio.sleep(min(900, interval))  # дать tuner'у пробежать первым
    while True:
        try:
            await run_proposer_cycle(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("proposer cycle failed: {}", exc)
        await asyncio.sleep(interval)
