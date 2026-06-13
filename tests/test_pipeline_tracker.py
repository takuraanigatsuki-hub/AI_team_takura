"""Pipeline tracker — шаги и авто-скрытие после завершения."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from room.pipeline_tracker import PipelineTracker


class FakeTaskHistory:
    def __init__(self, tasks=None):
        self.tasks = tasks or []

    def _find(self, task_id):
        for t in self.tasks:
            if t.get("id") == task_id:
                return t
        return None


def _room():
    rm = MagicMock()
    rm.task_history = FakeTaskHistory()
    rm.broadcast_work = AsyncMock()
    rm.agents = {
        "presenter": MagicMock(name="Ника", emoji="🎬"),
        "frontend": MagicMock(name="Маша", emoji="💜"),
    }
    return rm


def test_awaiting_approval_marks_step_done_and_finishes():
    room = _room()
    tracker = PipelineTracker(room)

    async def run():
        await tracker.start(
            "Сделай презентацию PowerPoint",
            {"presenter": "Слайды", "frontend": "Не трогать"},
            room.agents,
        )
        room.task_history.tasks = [
            {"id": "t1", "agent_id": "presenter", "task": "Слайды", "status": "awaiting_approval"},
            {"id": "t2", "agent_id": "frontend", "task": "Не трогать", "status": "awaiting_approval"},
        ]
        await tracker.on_task_completed("t1")
        await tracker.on_task_completed("t2")

    asyncio.run(run())

    assert tracker.active is not None
    assert tracker.active["finished_at"] is not None
    assert tracker.active["progress"] == 100
    worker_steps = [s for s in tracker.active["steps"] if s["agent_id"] in ("presenter", "frontend")]
    assert all(s["status"] == "done" for s in worker_steps)


def test_get_state_clears_stale_finished():
    room = _room()
    tracker = PipelineTracker(room)

    async def run():
        await tracker.start("Сделай презентацию PowerPoint", {"presenter": "x"}, room.agents)

    asyncio.run(run())
    tracker.active["finished_at"] = "2000-01-01T00:00:00"
    assert tracker.get_state() is None
    assert tracker.active is None


def test_auto_clear_broadcasts_null():
    room = _room()
    tracker = PipelineTracker(room)

    async def run():
        await tracker.start("Сделай презентацию PowerPoint", {"presenter": "x"}, room.agents)
        room.task_history.tasks = [
            {"id": "t1", "agent_id": "presenter", "task": "x", "status": "awaiting_approval"},
        ]
        await tracker.on_task_completed("t1")
        await asyncio.sleep(0.05)
        tracker._schedule_auto_clear(delay=0.01)
        await asyncio.sleep(0.05)

    asyncio.run(run())

    assert tracker.active is None
    calls = [c.args[0] for c in room.broadcast_work.call_args_list if c.args]
    assert any(c.get("pipeline") is None for c in calls)
