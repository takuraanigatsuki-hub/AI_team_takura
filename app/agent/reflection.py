"""Reflection — лёгкая форма «обучения без ML».

Раз в N часов:
  1. Читает последние journal-записи агента и ордера за то же окно.
  2. Считает реализованный P&L по парам buy/sell (FIFO).
  3. Спрашивает LLM: «вот что ты решал, вот что получилось — что усвоить?»
  4. Получает структурированный JSON {summary, rules_learned[]}.
  5. Сохраняет в таблицу agent_memos.

Memo на следующих циклах подмешивается в контекст агента (см. loop.py).
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..llm.client import LLMUnavailable, get_llm_client
from ..metrics.performance import _trade_win_rate  # noqa: F401  reused for stats
from ..models.db import AgentJournal, AgentMemo, Order


SYSTEM_PROMPT = """\
Ты — старший портфельный менеджер, который проводит ретроспективу решений
автономного торгового агента. Тебе показывают:
  • что агент решал в последние N циклов (его тезисы + действия);
  • что из этого реально исполнилось;
  • реализованный P&L по закрытым сделкам в этом окне.

Твоя задача — выписать КРАТКИЕ конкретные уроки, которые помогут агенту
действовать лучше в ближайшие сутки. Не общие фразы, а конкретные правила.

ОТВЕТ — строго валидный JSON одной верхней структуры:

{
  "summary": "1-3 предложения: что в целом получилось / не получилось",
  "rules_learned": [
    "Не открывай BTC long, если RSI > 75 — за последние 5 раз сделки в плюс не закрылись",
    "После убыточного дня уменьшай размер позиции вдвое до восстановления",
    ...
  ]
}

rules_learned: 2–6 правил. Каждое — короткое (одна фраза), конкретное, со
ссылкой на наблюдение из данных. Без воды, без советов общего характера.
Если данных мало или паттерн не виден — верни пустой массив rules_learned и
честный summary об этом.
"""


@dataclass
class ReflectionResult:
    summary: str
    rules: list[str]
    journal_count: int
    orders_count: int
    realized_pnl: float
    error: str = ""


def _collect_window(
    session,
    lookback_journal: int,
    since: datetime,
) -> tuple[list[dict], list[dict], float]:
    """Собрать journal-записи + ордера + посчитать реализованный P&L."""
    journal_rows = session.execute(
        select(AgentJournal).order_by(AgentJournal.ts.desc()).limit(lookback_journal)
    ).scalars().all()
    journal_data = []
    for row in reversed(journal_rows):
        try:
            executed = json.loads(row.executed) if row.executed else []
        except json.JSONDecodeError:
            executed = []
        journal_data.append({
            "ts": row.ts.isoformat(),
            "thesis": row.thesis,
            "executed": executed,
            "error": row.error,
        })

    order_rows = session.execute(
        select(Order).where(Order.created_at >= since).order_by(Order.created_at.asc())
    ).scalars().all()
    realized = _realized_pnl(order_rows)
    orders_data = [
        {
            "ts": o.created_at.isoformat(),
            "symbol": o.symbol, "side": o.side,
            "quantity": o.quantity, "price": o.price,
            "quote_amount": o.quote_amount, "reason": o.reason[:200],
        }
        for o in order_rows
    ]
    return journal_data, orders_data, realized


def _realized_pnl(orders) -> float:
    """FIFO-парирование buy→sell, сумма P&L по закрытым лотам."""
    from collections import defaultdict, deque

    queues: dict[str, deque] = defaultdict(deque)
    total = 0.0
    for o in sorted(orders, key=lambda x: (x.created_at, x.id)):
        if o.side == "buy":
            queues[o.symbol].append([o.quantity, o.price])
        elif o.side == "sell":
            remaining = o.quantity
            q = queues[o.symbol]
            while remaining > 1e-12 and q:
                lot_qty, lot_price = q[0]
                used = min(lot_qty, remaining)
                total += (o.price - lot_price) * used
                lot_qty -= used
                remaining -= used
                if lot_qty <= 1e-12:
                    q.popleft()
                else:
                    q[0][0] = lot_qty
    return round(total, 4)


def _parse_reflection(raw: str) -> tuple[str, list[str]]:
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
            return "(parse failed) " + text[:200], []
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return "(parse failed) " + text[:200], []
    if not isinstance(data, dict):
        return "(bad shape)", []
    summary = str(data.get("summary", "")).strip()[:600]
    rules_raw = data.get("rules_learned") or data.get("rules") or []
    rules: list[str] = []
    if isinstance(rules_raw, list):
        for r in rules_raw[:10]:
            if isinstance(r, str) and r.strip():
                rules.append(r.strip()[:240])
    return summary, rules


async def run_reflection(settings: Settings | None = None) -> ReflectionResult:
    """Выполнить один цикл рефлексии и записать memo, если данных достаточно."""
    s = settings or get_settings()
    since = datetime.now(timezone.utc) - timedelta(hours=s.reflection_interval_hours * 2)
    with session_scope() as session:
        journal, orders, realized = _collect_window(
            session, s.reflection_journal_lookback, since
        )
    if len(journal) < 3 and not orders:
        msg = "недостаточно данных для рефлексии (нужно >= 3 тиков агента)"
        return ReflectionResult(msg, [], len(journal), len(orders), realized, msg)

    user_prompt = (
        "## Тики агента (по возрастанию времени)\n"
        + f"```json\n{json.dumps(journal, ensure_ascii=False, indent=2)}\n```\n\n"
        + "## Сделки в этом окне\n"
        + f"```json\n{json.dumps(orders, ensure_ascii=False, indent=2)}\n```\n\n"
        + f"## Реализованный P&L по закрытым лотам: {realized:+.4f}\n\n"
        + "Сформулируй уроки в требуемом JSON."
    )

    try:
        client = get_llm_client()
        raw = await asyncio.to_thread(
            client.complete,
            SYSTEM_PROMPT, user_prompt,
            temperature=s.reflection_temperature,
            max_tokens=s.reflection_max_tokens,
            response_format_json=True,
        )
    except LLMUnavailable as exc:
        return ReflectionResult(f"LLM unavailable: {exc}", [], len(journal),
                                len(orders), realized, str(exc))

    summary, rules = _parse_reflection(raw)
    with session_scope() as session:
        session.add(AgentMemo(
            summary=summary,
            rules_learned=json.dumps(rules, ensure_ascii=False),
            journal_entries_reviewed=len(journal),
            orders_reviewed=len(orders),
            realized_pnl_window=realized,
            mode=s.mode,
        ))
    logger.info(
        "reflection saved: summary={!r} rules={} pnl={:+.2f}",
        summary[:80], len(rules), realized,
    )
    return ReflectionResult(summary, rules, len(journal), len(orders), realized)


async def reflection_loop(settings: Settings | None = None) -> None:
    """Запустить вечный цикл рефлексии."""
    s = settings or get_settings()
    if not s.reflection_enabled:
        return
    interval = max(3600, s.reflection_interval_hours * 3600)
    # первый цикл — через 30 минут после старта, чтобы успели накопиться тики
    await asyncio.sleep(min(1800, interval))
    while True:
        try:
            await run_reflection(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("reflection cycle failed: {}", exc)
        await asyncio.sleep(interval)
