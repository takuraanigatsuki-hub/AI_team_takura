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
        await self._check_finish()

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
        steps = self.active["steps"]
        if all(s.get("status") in ("done", "failed") for s in steps):
            self.active["finished_at"] = datetime.now().isoformat()
            self.active["progress"] = 100
            await self._broadcast()

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
        return self.active

    async def clear(self) -> None:
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
