"""Live pipeline — визуальный прогресс задачи по команде."""

import asyncio
from datetime import datetime
from typing import Optional

from room.task_routing import classify_task_kind


class PipelineTracker:
    def __init__(self, room_manager):
        self.room = room_manager
        self.active: Optional[dict] = None
        self._clear_task: Optional[asyncio.Task] = None

    def _progress(self) -> int:
        if not self.active:
            return 0
        steps = self.active.get("steps") or []
        if not steps:
            return 0
        done = sum(1 for s in steps if s.get("status") == "done")
        return int(done / len(steps) * 100)

    async def start(self, task_text: str, assignments: dict, agents: dict) -> None:
        steps = [{
            "id": "pm",
            "agent_id": "pm",
            "name": "Виктор",
            "emoji": "🎯",
            "label": "План команды",
            "status": "done",
        }]

        for agent_id, subtask in assignments.items():
            agent = agents.get(agent_id)
            steps.append({
                "id": agent_id,
                "agent_id": agent_id,
                "name": agent.name if agent else agent_id,
                "emoji": agent.emoji if agent else "🤖",
                "label": (subtask[:72] + "…") if len(subtask) > 72 else subtask,
                "status": "pending",
            })

        import config as cfg
        skip_github = classify_task_kind(task_text) in ("table", "presentation", "model_3d", "document")
        if (cfg.config.get("cursor_github_sync") or cfg.config.get("git_auto_sync")) and not skip_github:
            steps.append({
                "id": "github",
                "agent_id": "github",
                "name": "GitHub",
                "emoji": "📤",
                "label": "Sync & Deploy",
                "status": "pending",
            })

        self.active = {
            "task": task_text,
            "steps": steps,
            "progress": 0,
            "started_at": datetime.now().isoformat(),
            "finished_at": None,
        }
        await self._broadcast()

    async def on_task_started(self, task_id: str) -> None:
        if not self.active or not task_id:
            return
        task = self.room.task_history._find(task_id)
        if not task:
            return
        agent_id = task.get("agent_id") or task.get("target")
        await self._set_step(agent_id, "active")

    async def on_task_completed(self, task_id: str, failed: bool = False) -> None:
        if not self.active or not task_id:
            return
        task = self.room.task_history._find(task_id)
        if not task:
            return
        agent_id = task.get("agent_id") or task.get("target")
        await self._set_step(agent_id, "failed" if failed else "done")
        await self._sync_evaluator_step()
        await self._check_finish()

    def _evaluator_still_working(self) -> bool:
        if not self.active:
            return False
        parent_snippet = (self.active.get("task") or "")[:80]
        for t in self.room.task_history.tasks:
            if t.get("agent_id") != "evaluator":
                continue
            if t.get("status") not in ("queued", "in_progress", "submitted", "triaging"):
                continue
            blob = f"{t.get('task') or ''} {t.get('parent_id') or ''}"
            if parent_snippet and parent_snippet[:40] in blob:
                return True
            if t.get("parent_id"):
                parent = self.room.task_history._find(t["parent_id"])
                if parent and (parent.get("task") or "")[:80] == parent_snippet:
                    return True
        return False

    async def _sync_evaluator_step(self) -> None:
        """Evaluator часто работает inline — закрываем шаг, когда остальные готовы."""
        if not self.active or self._evaluator_still_working():
            return
        skip = {"evaluator", "pm", "github"}
        worker_steps = [s for s in self.active["steps"] if s.get("agent_id") not in skip]
        if not worker_steps:
            return
        if all(s.get("status") in ("done", "failed") for s in worker_steps):
            eval_step = next((s for s in self.active["steps"] if s.get("agent_id") == "evaluator"), None)
            if eval_step and eval_step.get("status") == "pending":
                await self._set_step("evaluator", "done")

    async def on_github(self, phase: str) -> None:
        if not self.active:
            return
        status = {"started": "active", "done": "done", "failed": "failed"}.get(phase, "active")
        await self._set_step("github", status)
        if status == "done":
            await self._check_finish()

    async def _set_step(self, agent_id: str, status: str) -> None:
        if not self.active:
            return
        for step in self.active["steps"]:
            if step.get("agent_id") == agent_id:
                step["status"] = status
                if status == "active":
                    step["started_at"] = datetime.now().isoformat()
                if status in ("done", "failed"):
                    step["finished_at"] = datetime.now().isoformat()
                break
        self.active["progress"] = self._progress()
        await self._broadcast()

    async def _check_finish(self) -> None:
        if not self.active:
            return
        await self._sync_evaluator_step()
        steps = self.active["steps"]
        if all(s.get("status") in ("done", "failed") for s in steps):
            self.active["finished_at"] = datetime.now().isoformat()
            self.active["progress"] = 100
            await self._broadcast()
            self._schedule_auto_clear()

    def _schedule_auto_clear(self, delay: float = 3.5) -> None:
        if self._clear_task and not self._clear_task.done():
            self._clear_task.cancel()

        async def _later():
            try:
                await asyncio.sleep(delay)
                if self.active and self.active.get("finished_at"):
                    await self.clear()
            except asyncio.CancelledError:
                pass

        self._clear_task = asyncio.create_task(_later())

    async def _broadcast(self) -> None:
        if not self.active:
            return
        payload = {
            "type": "pipeline_update",
            "pipeline": dict(self.active),
            "timestamp": datetime.now().isoformat(),
        }
        await self.room.broadcast_work(payload)

    def get_state(self) -> Optional[dict]:
        if not self.active:
            return None
        finished = self.active.get("finished_at")
        if finished:
            try:
                age = (datetime.now() - datetime.fromisoformat(finished)).total_seconds()
                if age > 25:
                    self.active = None
                    return None
            except Exception:
                pass
        return self.active

    async def clear(self) -> None:
        if self._clear_task and not self._clear_task.done():
            self._clear_task.cancel()
            self._clear_task = None
        self.active = None
        await self.room.broadcast_work({
            "type": "pipeline_update",
            "pipeline": None,
            "timestamp": datetime.now().isoformat(),
        })

    async def send_to(self, websocket) -> None:
        if self.active:
            import json
            await websocket.send_text(json.dumps({
                "type": "pipeline_update",
                "pipeline": dict(self.active),
                "timestamp": datetime.now().isoformat(),
            }, ensure_ascii=False))
