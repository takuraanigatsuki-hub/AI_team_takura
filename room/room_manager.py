import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket

from task_history import TaskHistory
from room.pipeline_tracker import PipelineTracker

LEARNING_TYPES = frozenset({
    "learning", "learning_result", "reflection", "rest", "figma_study",
    "peer_learning", "peer_discussion", "skill_evaluation",
})

WORK_TYPES = frozenset({
    "user_message", "system", "error", "task_received", "task_done",
    "assignment", "orchestrating", "pm_plan", "message", "site_ready",
    "react_preview", "cursor_progress", "cursor_run_done", "figma_import",
    "github_sync_started", "github_sync_done", "git_sync_done",
    "figma_portfolio", "pipeline_update", "agent_stream", "agent_stream_start",
    "agent_debate", "deploy_ready", "pr_ready", "artifact_created",
})


class RoomManager:
    """Менеджер комнаты — координирует всех агентов и WebSocket соединения"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_meta: Dict[WebSocket, dict] = {}
        self._visitor_counter = 0
        self.agents: Dict[str, Any] = {}
        self.work_history = []
        self.learning_history = []
        self.max_history = 500
        self.task_history = TaskHistory()
        self.pipeline = PipelineTracker(self)
        self._last_submitted_id: Optional[str] = None
        self.current_plan: Optional[dict] = None

    def register_agent(self, agent):
        self.agents[agent.agent_id] = agent
        agent.room_manager = self

    def _channel_for(self, msg_type: str) -> str:
        if msg_type in LEARNING_TYPES:
            return "learning"
        return "work"

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        self._visitor_counter += 1
        vid = f"guest-{self._visitor_counter}"
        self.connection_meta[websocket] = {
            "id": vid,
            "name": f"Guest {self._visitor_counter}",
            "joined_at": datetime.now().isoformat(),
        }

        if self.work_history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "channel": "work",
                "messages": self.work_history[-100:]
            }, ensure_ascii=False))

        if self.learning_history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "channel": "learning",
                "messages": self.learning_history[-100:]
            }, ensure_ascii=False))

        await websocket.send_text(json.dumps({
            "type": "agents_state",
            "agents": [agent.get_state() for agent in self.agents.values()]
        }, ensure_ascii=False))

        await websocket.send_text(json.dumps({
            "type": "task_history",
            "stats": self.task_history.stats(),
            "tasks": self.task_history.get_all()[:80],
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))

        if self.current_plan:
            await websocket.send_text(json.dumps({
                "type": "pm_plan",
                "agent_id": "pm",
                "agent_name": "Виктор",
                "agent_emoji": "🎯",
                "message": self.current_plan.get("plan", ""),
                "task": self.current_plan.get("task", ""),
                "channel": "work",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False))

        await self.pipeline.send_to(websocket)
        await self._broadcast_presence(exclude=websocket)

        await self.broadcast_work({
            "type": "system",
            "message": "🟢 Пользователь подключился к комнате",
            "timestamp": datetime.now().isoformat()
        }, exclude=websocket)

    async def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.connection_meta.pop(websocket, None)
        await self._broadcast_presence()
        await self.broadcast_work({
            "type": "system",
            "message": "🔴 Пользователь покинул комнату",
            "timestamp": datetime.now().isoformat()
        })

    def _append_history(self, message: dict, channel: str):
        message["channel"] = channel
        try:
            from integrations.timeline_store import append_event
            append_event({
                "type": message.get("type"),
                "agent_id": message.get("agent_id"),
                "agent_name": message.get("agent_name"),
                "message": (message.get("message") or "")[:200],
                "timestamp": message.get("timestamp"),
            })
        except Exception:
            pass
        if channel == "learning":
            self.learning_history.append(message)
            if len(self.learning_history) > self.max_history:
                self.learning_history = self.learning_history[-self.max_history:]
        else:
            self.work_history.append(message)
            if len(self.work_history) > self.max_history:
                self.work_history = self.work_history[-self.max_history:]

    async def _broadcast_presence(self, exclude: WebSocket = None):
        visitors = [
            {"id": m["id"], "name": m["name"]}
            for m in self.connection_meta.values()
        ]
        await self.broadcast({
            "type": "presence_update",
            "count": len(visitors),
            "visitors": visitors,
            "timestamp": datetime.now().isoformat(),
        }, exclude=exclude)

    async def broadcast(self, message: dict, exclude: WebSocket = None):
        """Обратная совместимость — маршрутизация по каналу."""
        ch = message.get("channel") or self._channel_for(message.get("type", ""))
        message["channel"] = ch
        self._append_history(message, ch)
        await self._send_to_clients(message, exclude)

    async def broadcast_work(self, message: dict, exclude: WebSocket = None):
        message["channel"] = "work"
        self._append_history(message, "work")
        await self._send_to_clients(message, exclude)

    async def broadcast_learning(self, message: dict, exclude: WebSocket = None):
        message["channel"] = "learning"
        self._append_history(message, "learning")
        await self._send_to_clients(message, exclude)

    async def _send_to_clients(self, message: dict, exclude: WebSocket = None):
        message_text = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        for connection in self.active_connections:
            if connection == exclude:
                continue
            try:
                await connection.send_text(message_text)
            except Exception:
                disconnected.add(connection)
        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_agents_state(self):
        await self.broadcast({
            "type": "agents_state",
            "agents": [agent.get_state() for agent in self.agents.values()]
        })

    def has_pending_work(self) -> bool:
        """Есть ли в комнате активные задачи (статистика/UI, не блокирует обучение).

        Обучение решается per-agent в BaseAgent._work_mode_active().
        """
        blocking = ("queued", "in_progress", "triaging", "revision_requested")
        if any(t.get("status") in blocking for t in self.task_history.tasks):
            return True
        for agent in self.agents.values():
            if not agent.task_queue.empty():
                return True
        return False

    def agent_is_busy(self, agent_id: str) -> bool:
        """Занят ли конкретный агент задачей."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False
        if not agent.task_queue.empty():
            return True
        return agent.status in ("working", "thinking")

    async def handle_user_message(self, data: dict):
        msg_type = data.get("type", "task")
        target = data.get("target", "all")
        text = data.get("text", "")

        if not text.strip():
            return

        from room.mention_parser import parse_mentions
        from room.user_intent import record_user_wish
        text, mention_target = parse_mentions(text)
        if mention_target:
            target = mention_target

        if not text.strip():
            return

        await self.broadcast_work({
            "type": "user_message",
            "message": text,
            "target": target,
            "timestamp": datetime.now().isoformat()
        })

        if msg_type == "task":
            record_user_wish(text, target if target not in ("all", "pm") else None)
            self._last_submitted_id = self.task_history.add_submitted(text, target, msg_type)
            await self._broadcast_task_history()

            if target == "all":
                pm = self.agents.get("pm")
                if pm:
                    await pm.orchestrate_task(text, self.agents, parent_id=self._last_submitted_id)
                else:
                    for agent in self.agents.values():
                        child_id = self.task_history.add_queued(
                            text, agent.agent_id, agent.name, agent.emoji,
                            parent_id=self._last_submitted_id, sender="Пользователь"
                        )
                        await agent.assign_task(
                            text, sender="Пользователь",
                            parent_id=self._last_submitted_id, task_id=child_id
                        )
            elif target == "pm":
                pm = self.agents.get("pm")
                if pm:
                    await pm.orchestrate_task(text, self.agents, parent_id=self._last_submitted_id)
            else:
                agent = self.agents.get(target)
                if agent:
                    child_id = self.task_history.add_queued(
                        text, target, agent.name, agent.emoji,
                        parent_id=self._last_submitted_id, sender="Пользователь"
                    )
                    await agent.assign_task(
                        text, sender="Пользователь",
                        parent_id=self._last_submitted_id, task_id=child_id
                    )
                else:
                    await self.broadcast_work({
                        "type": "error",
                        "message": f"Агент '{target}' не найден",
                        "timestamp": datetime.now().isoformat()
                    })

            await self._maybe_github_sync(text)

        elif msg_type == "chat":
            record_user_wish(text, target if target not in ("all", None) else "pm")
            if target == "all":
                pm = self.agents.get("pm")
                if pm:
                    await pm.handle_direct_chat(text, force_chat=True)
            else:
                agent = self.agents.get(target)
                if agent:
                    await agent.handle_direct_chat(text, force_chat=True)
                else:
                    await self.broadcast_work({
                        "type": "error",
                        "message": f"Агент '{target}' не найден",
                        "timestamp": datetime.now().isoformat()
                    })

        elif msg_type == "direct_chat":
            agent = self.agents.get(target)
            if agent:
                await agent.handle_direct_chat(text)
            else:
                await self.broadcast_work({
                    "type": "error",
                    "message": f"Агент '{target}' не найден",
                    "timestamp": datetime.now().isoformat()
                })

    async def start_all_agents(self):
        for agent in self.agents.values():
            await agent.start()

        await self.broadcast_work({
            "type": "system",
            "message": "🚀 Все агенты запущены и готовы к работе!",
            "timestamp": datetime.now().isoformat()
        })

    async def stop_all_agents(self):
        for agent in self.agents.values():
            await agent.stop()

    async def state_broadcaster(self):
        while True:
            await asyncio.sleep(3)
            if self.active_connections:
                await self.send_agents_state()

    async def _broadcast_task_history(self):
        await self.broadcast({
            "type": "task_history",
            "stats": self.task_history.stats(),
            "tasks": self.task_history.get_all()[:80],
            "timestamp": datetime.now().isoformat()
        })

    def record_task_started(self, task_id: str):
        if task_id:
            self.task_history.mark_in_progress(task_id)
            asyncio.create_task(self.pipeline.on_task_started(task_id))

    def record_task_completed(self, task_id: str, response: str,
                              agent_name: str = "", agent_emoji: str = ""):
        if task_id:
            self.task_history.mark_completed(task_id, response, agent_name, agent_emoji)
            asyncio.create_task(self.pipeline.on_task_completed(task_id, failed=False))

    def record_task_awaiting_approval(
        self, task_id: str, response: str, agent_name: str = "", agent_emoji: str = "",
        artifact_id: str = None, preview_url: str = None,
    ):
        if task_id:
            self.task_history.mark_awaiting_approval(
                task_id, response, agent_name, agent_emoji, artifact_id, preview_url,
            )
            asyncio.create_task(self._broadcast_task_history())
            asyncio.create_task(self.broadcast_work({
                "type": "task_awaiting_approval",
                "task_id": task_id,
                "agent_name": agent_name,
                "agent_emoji": agent_emoji,
                "message": (
                    f"⏳ **{agent_name}** завершил работу — нужно ваше подтверждение.\n"
                    f"Откройте вкладку **Задачи** → ✓ Принять или ✎ Правки."
                ),
                "timestamp": datetime.now().isoformat(),
            }))

    async def approve_task(self, task_id: str, note: str = "") -> bool:
        t = self.task_history._find(task_id)
        if not t or t.get("status") != "awaiting_approval":
            return False
        self.task_history.mark_user_approved(task_id, note)
        await self.pipeline.on_task_completed(task_id, failed=False)
        await self.broadcast_work({
            "type": "task_approved",
            "task_id": task_id,
            "message": f"✅ Задача принята пользователем{f': {note}' if note else ''}.",
            "timestamp": datetime.now().isoformat(),
        })
        await self._broadcast_task_history()
        return True

    async def request_task_revision(self, task_id: str, feedback: str) -> bool:
        t = self.task_history._find(task_id)
        if not t or t.get("status") != "awaiting_approval":
            return False
        agent_id = t.get("agent_id")
        agent = self.agents.get(agent_id)
        self.task_history.mark_revision_requested(task_id, feedback)
        if agent:
            revision_text = f"{t.get('task', '')}\n\n✎ Правки пользователя: {feedback}"
            child_id = self.task_history.add_queued(
                revision_text, agent_id, agent.name, agent.emoji,
                parent_id=t.get("parent_id"), sender="Пользователь",
            )
            await agent.assign_task(
                revision_text, sender="Пользователь (правки)",
                parent_id=t.get("parent_id"), task_id=child_id,
            )
        await self.broadcast_work({
            "type": "task_revision",
            "task_id": task_id,
            "message": f"✎ Отправлено на доработку: {feedback[:200]}",
            "timestamp": datetime.now().isoformat(),
        })
        await self._broadcast_task_history()
        return True

    def record_task_failed(self, task_id: str, error: str = ""):
        if task_id:
            self.task_history.mark_failed(task_id, error)
            asyncio.create_task(self.pipeline.on_task_completed(task_id, failed=True))

    async def _maybe_github_sync(self, task_text: str):
        """GitHub Sync только для явных coding-задач (не таблицы/UI/презентации)."""
        from room.task_routing import should_sync_to_github

        if not should_sync_to_github(task_text):
            return
        try:
            from integrations.github_sync import sync_task_to_github
            await sync_task_to_github(task_text, room_manager=self, source="task")
        except Exception as e:
            await self.broadcast_work({
                "type": "system",
                "message": f"⚠️ GitHub Sync (Cloud): {e}",
                "timestamp": datetime.now().isoformat(),
            })
        try:
            from integrations.local_git_sync import sync_after_task
            await sync_after_task(task_text, room_manager=self)
        except Exception as e:
            await self.broadcast_work({
                "type": "system",
                "message": f"⚠️ Git Sync (local): {e}",
                "timestamp": datetime.now().isoformat(),
            })
