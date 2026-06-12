#!/usr/bin/env python3
"""Проверка Сони — задачи, Figma Studio, React Preview."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.figma_rate_limit import reset_cooldown
from integrations.figma_learning import ensure_seed_patterns, run_figma_study_session, run_figma_create_session
from agents.react_preview import generate_react_preview
from agents.frontend_dev import FrontendDevAgent


SONYA_TASKS = [
    "Создай форму регистрации в React с валидацией email",
    "Сделай landing page для AI-стартапа с hero и CTA",
    "Dashboard с KPI карточками и графиком активности",
    "Карточка товара для e-commerce с кнопкой «Купить»",
    "Навигационное меню с логотипом и пунктами",
]


async def main():
    reset_cooldown()
    ensure_seed_patterns()

    print("=== React Preview шаблоны ===")
    for task in SONYA_TASKS:
        p = generate_react_preview(task)
        ok = bool(p.get("code") and len(p["code"]) > 100)
        print(f"{'OK' if ok else 'FAIL'} · {p.get('title')} · {task[:50]}")

    print("\n=== Figma Studio (offline) ===")

    class FakeRoom:
        async def broadcast_learning(self, *_a, **_k):
            pass

        async def broadcast_work(self, *_a, **_k):
            pass

        async def send_agents_state(self):
            pass

    async def noop(*_a, **_k):
        pass

    agent = FrontendDevAgent(FakeRoom())
    agent._persist_knowledge = lambda: None
    agent._broadcast = noop

    from unittest.mock import patch
    with patch("integrations.figma_learning.random.random", return_value=0.0):
        study = await run_figma_study_session(agent)
    create = await run_figma_create_session(agent)
    print(f"study={'OK' if study else 'FAIL'}  create={'OK' if create else 'FAIL'}")
    print(f"preview_title={getattr(agent, 'last_preview', {}) and agent.last_preview.get('title')}")

    print("\nГотово.")


if __name__ == "__main__":
    asyncio.run(main())
