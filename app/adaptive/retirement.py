"""Авто-отключение хронически убыточных стратегий.

Каждые N часов:
  1. Считает performance snapshots за последнее окно.
  2. Для каждой стратегии, у которой:
       - created_by != 'user' (то есть появилась от tuner/llm/ga),
       - decisive_votes >= min_decisions,
       - attributable_pnl < threshold (по умолчанию -3%),
     ставит enabled=0 и пишет note с причиной.

Это защищает портфель от роста «плохих» стратегий, которые tuner или
LLM создал, но они не оправдали ожиданий в реальной торговле.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..core.database import session_scope
from ..core.logging import logger
from ..models.db import StrategyConfig
from .weights import compute_performance_snapshots


@dataclass
class RetirementResult:
    retired: list[str]
    kept: int
    skipped_protected: int  # стратегии created_by='user' не трогаем


def run_retirement_cycle(settings: Settings | None = None) -> RetirementResult:
    s = settings or get_settings()
    if not s.retirement_enabled:
        return RetirementResult([], 0, 0)

    with session_scope() as session:
        snapshots = compute_performance_snapshots(
            session, lookback=s.adaptive_lookback_decisions
        )
        snap_by_name = {sn.strategy_name: sn for sn in snapshots}

        configs = session.execute(
            select(StrategyConfig).where(StrategyConfig.enabled == 1)
        ).scalars().all()

        retired: list[str] = []
        kept = 0
        skipped = 0

        for config in configs:
            if config.created_by == "user":
                skipped += 1
                kept += 1
                continue
            sn = snap_by_name.get(config.name)
            if sn is None:
                kept += 1
                continue
            if sn.decisive_votes < s.retirement_min_decisions:
                kept += 1
                continue
            if sn.attributable_pnl < s.retirement_pnl_threshold:
                config.enabled = 0
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
                config.note = (
                    f"[retired {ts}] decisive={sn.decisive_votes} "
                    f"attr_pnl={sn.attributable_pnl:+.2f} (threshold {s.retirement_pnl_threshold})"
                )
                retired.append(config.name)
            else:
                kept += 1

    if retired:
        logger.info("retirement: disabled {} strategies: {}",
                    len(retired), ", ".join(retired[:5]) + ("..." if len(retired) > 5 else ""))
    return RetirementResult(retired=retired, kept=kept, skipped_protected=skipped)


async def retirement_loop(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    if not s.retirement_enabled:
        return
    interval = max(1800, s.retirement_interval_hours * 3600)
    await asyncio.sleep(min(3600, interval))
    while True:
        try:
            run_retirement_cycle(s)
        except Exception as exc:  # noqa: BLE001
            logger.exception("retirement cycle failed: {}", exc)
        await asyncio.sleep(interval)
