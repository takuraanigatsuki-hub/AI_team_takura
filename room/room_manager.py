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

# Только обучение — никогда не попадает в рабочий чат
STUDY_TYPES = frozenset({
    "learning", "learning_result", "reflection", "rest", "figma_study",
    "peer_learning", "peer_discussion", "learning_project", "skill_evaluation",
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
        self.learning_projects = None
        self.active_workspace_id: str = ""

    def _learning_store(self):
        if self.learning_projects is None:
            from room.learning_projects import LearningProjects
            self.learning_projects = LearningProjects()
        return self.learning_projects

    def register_agent(self, agent):
        self.agents[agent.agent_id] = agent
        agent.room_manager = self

    def _channel_for(self, msg_type: str) -> str:
        if msg_type in LEARNING_TYPES:
            return "learning"
        return "work"

    async def connect(self, websocket: WebSocket, user=None, view_token=None, readonly: bool = False):
        await websocket.accept()
        self.active_connections.add(websocket)
        self._visitor_counter += 1
        if user:
            vid = user.get("id", f"user-{self._visitor_counter}")
            name = user.get("name") or user.get("email", "User").split("@")[0]
        else:
            vid = f"guest-{self._visitor_counter}"
            name = f"Guest {self._visitor_counter}"
        self.connection_meta[websocket] = {
            "id": vid,
            "name": name,
            "user_id": user.get("id") if user else vid,
            "role": user.get("role", "guest") if user else "guest",
            "readonly": readonly,
            "view_token": view_token,
            "joined_at": datetime.now().isoformat(),
        }

        if user and user.get("id"):
            from room.message_filter import is_privileged
            if not is_privileged(user.get("role", "")):
                self.task_history.claim_orphans_for_user(
                    user.get("id", ""),
                    user.get("email", ""),
                    user.get("name", ""),
                )

        meta = self.connection_meta[websocket]
        viewer = {"user_id": meta.get("user_id", ""), "role": meta.get("role", "guest")}
        from room.message_filter import filter_messages_for_viewer, filter_agents_for_viewer

        if self.work_history:
            work_msgs = filter_messages_for_viewer(self.work_history[-100:], viewer)
            await websocket.send_text(json.dumps({
                "type": "history",
                "channel": "work",
                "messages": work_msgs
            }, ensure_ascii=False))

        if self.learning_history:
            await websocket.send_text(json.dumps({
                "type": "history",
                "channel": "learning",
                "messages": self.learning_history[-100:]
            }, ensure_ascii=False))

        await websocket.send_text(json.dumps({
            "type": "agents_state",
            "agents": filter_agents_for_viewer(
                [agent.get_state() for agent in self.agents.values()], viewer),
        }, ensure_ascii=False))

        await websocket.send_text(json.dumps(
            self._task_history_payload(viewer), ensure_ascii=False))

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
        msg_type = message.get("type", "")
        if msg_type in STUDY_TYPES:
            return await self.broadcast_learning(message, exclude)
        message["channel"] = "work"
        self._append_history(message, "work")
        await self._send_to_clients(message, exclude)

    async def broadcast_learning(self, message: dict, exclude: WebSocket = None):
        message["channel"] = "learning"
        self._append_history(message, "learning")
        await self._send_to_clients(message, exclude)

    def _task_history_payload(self, viewer: dict) -> dict:
        from room.message_filter import is_privileged
        role = viewer.get("role", "")
        uid = viewer.get("user_id", "")
        if is_privileged(role):
            tasks = self.task_history.get_all()[:80]
            stats = self.task_history.stats()
        else:
            tasks = self.task_history.get_for_user(uid, 80)
            stats = self.task_history.stats_for_user(uid)
        return {
            "type": "task_history",
            "stats": stats,
            "tasks": tasks,
            "timestamp": datetime.now().isoformat(),
        }

    async def _send_to_clients(self, message: dict, exclude: WebSocket = None):
        from room.message_filter import should_show_message, filter_agents_for_viewer
        msg_copy = dict(message)
        if msg_copy.get("type") == "agents_state" and msg_copy.get("agents"):
            disconnected = set()
            for connection in self.active_connections:
                if connection == exclude:
                    continue
                meta = self.connection_meta.get(connection, {})
                viewer = {"user_id": meta.get("user_id", ""), "role": meta.get("role", "guest")}
                payload = dict(msg_copy)
                payload["agents"] = filter_agents_for_viewer(msg_copy["agents"], viewer)
                try:
                    await connection.send_text(json.dumps(payload, ensure_ascii=False))
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.active_connections.discard(conn)
            return

        if msg_copy.get("type") == "task_history":
            disconnected = set()
            for connection in self.active_connections:
                if connection == exclude:
                    continue
                meta = self.connection_meta.get(connection, {})
                viewer = {"user_id": meta.get("user_id", ""), "role": meta.get("role", "guest")}
                try:
                    await connection.send_text(json.dumps(
                        self._task_history_payload(viewer), ensure_ascii=False))
                except Exception:
                    disconnected.add(connection)
            for conn in disconnected:
                self.active_connections.discard(conn)
            return

        disconnected = set()
        for connection in self.active_connections:
            if connection == exclude:
                continue
            meta = self.connection_meta.get(connection, {})
            viewer = {"user_id": meta.get("user_id", ""), "role": meta.get("role", "guest")}
            if not should_show_message(msg_copy, viewer):
                continue
            try:
                await connection.send_text(json.dumps(msg_copy, ensure_ascii=False))
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

    async def _handle_learning_command(self, parsed: dict):
        """Slash /learn /practice /collab /маша — учебные проекты, не вкладка Задачи."""
        text = (parsed.get("text") or parsed.get("label") or "Упражнение").strip()
        collaborative = parsed.get("collaborative", False)
        cmd = parsed.get("cmd", "learn")
        store = self._learning_store()

        if cmd in ("practice", "collab", "learn") and collaborative:
            agent_ids = ["frontend", "backend", "qa"]
        elif cmd == "practice":
            agent_ids = ["frontend", "backend"]
        elif parsed.get("target") == "evaluator":
            agent_ids = ["frontend"]
        else:
            agent_ids = ["frontend", "backend"] if collaborative else ["frontend"]

        project = store.create_user_submission(
            title=text[:120],
            description=text,
            collaborative=collaborative,
            cmd=cmd,
            target_agents=agent_ids,
        )

        ev = self.agents.get("evaluator")
        ev_name = ev.name if ev else "Маша"
        ev_emoji = ev.emoji if ev else "🎓"

        await self.broadcast_learning({
            "type": "learning_project",
            "project": project,
            "agent_id": "evaluator",
            "agent_name": ev_name,
            "agent_emoji": ev_emoji,
            "message": (
                f"🎓 **{ev_name}** приняла упражнение:\n_{project['title']}_\n"
                f"{'🤝 Совместная практика' if collaborative else '📚 Индивидуальная практика'}"
            ),
            "timestamp": datetime.now().isoformat(),
        })

        for aid in agent_ids[:3 if collaborative else 2]:
            agent = self.agents.get(aid)
            if agent and not self.agent_is_busy(aid):
                asyncio.create_task(self._agent_learning_practice(agent, text, project["id"], collaborative))

        await self.broadcast_work({
            "type": "system",
            "message": (
                f"📚 Упражнение отправлено в **Обучение → Маша**. "
                f"Агенты: {', '.join(agent_ids[:3])}."
            ),
            "timestamp": datetime.now().isoformat(),
        })

    async def _agent_learning_practice(
        self, agent, topic: str, project_id: str, collaborative: bool = False,
    ):
        """Короткая практика без очереди задач."""
        if agent.task_queue.empty() is False:
            return
        try:
            agent.status = "learning"
            agent.location = "library"
            await agent._broadcast_learning(f"📚 Практика: *{topic[:80]}*", "learning")
            material = await agent._fetch_learning_material(topic)
            summary = material.get("summary", topic)[:300] if material else topic[:200]
            title = material.get("title", topic)[:80] if material else topic[:80]

            co_ids = []
            if collaborative:
                for aid, other in self.agents.items():
                    if aid != agent.agent_id and aid not in ("pm", "evaluator") and not self.agent_is_busy(aid):
                        co_ids.append(aid)
                        if len(co_ids) >= 2:
                            break

            store = self._learning_store()
            proj = store.create_agent_project(
                agent.agent_id,
                title=title,
                summary=summary,
                collaborative=bool(co_ids),
                co_agent_ids=co_ids,
                topic=topic,
            )

            await agent._broadcast_learning(
                f"💡 **Проект практики:** _{title}_\n{summary[:200]}",
                "learning_result",
            )

            evaluator = self.agents.get("evaluator")
            if evaluator and hasattr(evaluator, "evaluate_output"):
                result = await evaluator.evaluate_output(
                    topic, agent.agent_id, agent.name, summary, context="peer_learning",
                )
                store.add_evaluation(
                    agent.agent_id,
                    result.get("score", 7),
                    result.get("feedback", ""),
                    task=topic,
                    context="learning_practice",
                    project_id=proj["id"],
                )
                await self.broadcast_learning({
                    "type": "skill_evaluation",
                    "agent_id": "evaluator",
                    "agent_name": evaluator.name,
                    "agent_emoji": evaluator.emoji,
                    "project_id": proj["id"],
                    "score": result.get("score", 7),
                    "message": (
                        f"🎓 **Оценка ({result.get('score', 7)}/10)** · {agent.name}\n"
                        f"{result.get('feedback', '')[:350]}"
                    ),
                    "timestamp": datetime.now().isoformat(),
                })
        except Exception:
            pass
        finally:
            agent.status = "idle"
            agent.location = "studio"

    def _actor_identity(self, user=None, connection_meta=None) -> tuple:
        """user_id и display name отправителя (в т.ч. guest-N для анонимов)."""
        if user:
            uid = user.get("id", "")
            uname = user.get("name") or user.get("email", "User").split("@")[0]
        elif connection_meta:
            uid = connection_meta.get("user_id") or connection_meta.get("id", "")
            uname = connection_meta.get("name", "Guest")
        else:
            uid, uname = "", ""
        return uid, uname

    async def handle_user_message(self, data: dict, user=None, connection_meta=None):
        msg_type = data.get("type", "task")

        if msg_type == "task_approve":
            uid, _ = self._actor_identity(user, connection_meta)
            task_id = data.get("task_id", "")
            if not task_id or not self.task_history.user_owns_task(task_id, uid, False):
                await self.broadcast_work({
                    "type": "error",
                    "message": "🔒 Нет доступа к этой задаче",
                    "timestamp": datetime.now().isoformat(),
                })
                return
            if await self.approve_task(task_id, data.get("note", "") or ""):
                await self._broadcast_task_history()
            else:
                await self.broadcast_work({
                    "type": "error",
                    "message": "Задача не ждёт подтверждения",
                    "timestamp": datetime.now().isoformat(),
                })
            return

        if msg_type == "task_revision":
            uid, _ = self._actor_identity(user, connection_meta)
            task_id = data.get("task_id", "")
            feedback = (data.get("feedback") or "").strip()
            if not task_id or not self.task_history.user_owns_task(task_id, uid, False):
                await self.broadcast_work({
                    "type": "error",
                    "message": "🔒 Нет доступа к этой задаче",
                    "timestamp": datetime.now().isoformat(),
                })
                return
            if not feedback:
                await self.broadcast_work({
                    "type": "error",
                    "message": "Укажите текст правок",
                    "timestamp": datetime.now().isoformat(),
                })
                return
            if await self.request_task_revision(task_id, feedback):
                await self._broadcast_task_history()
            else:
                await self.broadcast_work({
                    "type": "error",
                    "message": "Задача не ждёт подтверждения",
                    "timestamp": datetime.now().isoformat(),
                })
            return

        if msg_type == "task_cancel_all":
            uid, _ = self._actor_identity(user, connection_meta)
            from room.message_filter import is_privileged
            privileged = bool(user and is_privileged(user.get("role", "")))
            count = await self.cancel_all_tasks(user_id=uid, privileged=privileged)
            await self._broadcast_task_history()
            await self.broadcast_work({
                "type": "system",
                "message": f"🛑 Отменено активных задач: {count}",
                "timestamp": datetime.now().isoformat(),
            })
            return

        if msg_type == "task_priority":
            uid, _ = self._actor_identity(user, connection_meta)
            task_id = data.get("task_id", "")
            priority = data.get("priority", "medium")
            if not task_id or not self.task_history.user_owns_task(task_id, uid, False):
                await self.broadcast_work({
                    "type": "error",
                    "message": "🔒 Нет доступа к этой задаче",
                    "timestamp": datetime.now().isoformat(),
                })
                return
            if self.task_history.set_priority(task_id, priority):
                await self._broadcast_task_history()
            return

        target = data.get("target", "all")
        raw_text = data.get("text", "")

        if not raw_text.strip():
            return

        from room.slash_commands import parse_slash_command, help_text
        parsed = parse_slash_command(raw_text)
        if parsed:
            if parsed.get("show_help"):
                await self.broadcast_work({
                    "type": "system",
                    "message": help_text(),
                    "timestamp": datetime.now().isoformat(),
                })
                return
            if parsed.get("learning_mode") or parsed.get("msg_type") == "learning":
                await self._handle_learning_command(parsed)
                return
            msg_type = parsed.get("msg_type") or msg_type
            if parsed.get("target"):
                target = parsed["target"]
            raw_text = parsed.get("text") or raw_text

        text = raw_text
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
            if user:
                from room.task_limits import check_and_record
                from room.user_auth import charge_user_action
                ok, msg = check_and_record(user)
                if not ok:
                    await self.broadcast_work({
                        "type": "error",
                        "message": f"⚠️ {msg}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    return
                ok, msg = charge_user_action(user.get("id", ""), "task")
                if not ok:
                    await self.broadcast_work({
                        "type": "error",
                        "message": f"⚠️ {msg}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    return

            uid, uname = self._actor_identity(user, connection_meta)

            try:
                from room.workspaces import get_active
                self.active_workspace_id = get_active(uid) if uid else ""
            except Exception:
                self.active_workspace_id = ""

            dup = self.task_history.find_active_duplicate(text, uid)
            if dup:
                await self.broadcast_work({
                    "type": "system",
                    "message": (
                        f"ℹ️ Такая задача уже в работе (статус: **{dup.get('status')}**). "
                        f"Смотрите вкладку **Задачи** — дубликат не создан."
                    ),
                    "timestamp": datetime.now().isoformat(),
                })
                await self._broadcast_task_history()
                return

            record_user_wish(text, target if target not in ("all", "pm") else None)
            self._last_submitted_id = self.task_history.add_submitted(
                text, target, msg_type, uid, uname)
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
            uid, uname = self._actor_identity(user, connection_meta)
            if target == "all":
                pm = self.agents.get("pm")
                if pm:
                    await pm.handle_direct_chat(text, force_chat=True, user_id=uid, user_name=uname)
            else:
                agent = self.agents.get(target)
                if agent:
                    await agent.handle_direct_chat(text, force_chat=True, user_id=uid, user_name=uname)
                else:
                    await self.broadcast_work({
                        "type": "error",
                        "message": f"Агент '{target}' не найден",
                        "timestamp": datetime.now().isoformat()
                    })

        elif msg_type == "direct_chat":
            agent = self.agents.get(target)
            uid, uname = self._actor_identity(user, connection_meta)
            if agent:
                await agent.handle_direct_chat(text, user_id=uid, user_name=uname)
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

    async def _broadcast_task_history(self, exclude: WebSocket = None):
        await self._send_to_clients({"type": "task_history"}, exclude)

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
        if not task_id:
            return
        self.task_history.mark_awaiting_approval(
            task_id, response, agent_name, agent_emoji, artifact_id, preview_url,
        )
        asyncio.create_task(self.pipeline.on_task_completed(task_id, failed=False))
        asyncio.create_task(self._broadcast_task_history())
        t = self.task_history._find(task_id)
        notify_id = task_id
        if t and t.get("parent_id"):
            parent = self.task_history._find(t["parent_id"])
            if parent and parent.get("status") == "awaiting_approval":
                notify_id = parent["id"]
            else:
                return
        asyncio.create_task(self._pm_notify_user_approval(notify_id))

    async def _pm_notify_user_approval(self, task_id: str):
        """Единое уведомление о проверке — только от PM (Виктор)."""
        t = self.task_history._find(task_id)
        if not t or t.get("status") != "awaiting_approval":
            return
        if t.get("approval_notified"):
            return

        pm = self.agents.get("pm")
        pm_name = pm.name if pm else "Виктор"
        pm_emoji = pm.emoji if pm else "🎯"

        children = [c for c in self.task_history.tasks if c.get("parent_id") == task_id]
        lines = []
        site_url = None
        preview_url = None
        for c in children:
            if c.get("status") != "awaiting_approval":
                continue
            who = f"{c.get('agent_emoji', '')} {c.get('agent_name', 'Агент')}".strip()
            snippet = (c.get("response") or "")[:140]
            lines.append(f"• **{who}**: {snippet}{'…' if len(c.get('response') or '') > 140 else ''}")
            if c.get("preview_url"):
                preview_url = c["preview_url"]
            if c.get("agent_id") == "frontend" and not site_url:
                site_url = c.get("preview_url") or "/api/sites/latest"

        if not lines and t.get("response"):
            lines.append((t.get("response") or "")[:400])

        t["approval_notified"] = True
        self.task_history._save()

        task_title = (t.get("task") or "")[:220]
        msg = (
            f"⏳ **Команда завершила работу** — нужно ваше подтверждение.\n\n"
            f"**Задача:** _{task_title}_\n\n"
        )
        if lines:
            msg += "\n".join(lines[:8]) + "\n\n"
        msg += "Откройте вкладку **Задачи** → ✓ Принять или ✎ Правки."

        await self.broadcast_work({
            "type": "task_awaiting_approval",
            "task_id": task_id,
            "agent_id": "pm",
            "agent_name": pm_name,
            "agent_emoji": pm_emoji,
            "site_url": site_url or preview_url,
            "preview_url": preview_url,
            "message": msg,
            "timestamp": datetime.now().isoformat(),
        })
        try:
            from room import notifications
            uid = t.get("user_id") or ""
            if uid:
                notifications.push(
                    "⏳ Задача ждёт вашего решения",
                    task_title[:200],
                    user_id=uid,
                    ntype="task",
                    link="/app#tasks",
                )
        except Exception:
            pass

    async def approve_task(self, task_id: str, note: str = "") -> bool:
        t = self.task_history._find(task_id)
        if not t or t.get("status") != "awaiting_approval":
            return False
        self.task_history.mark_user_approved(task_id, note)
        await self.pipeline.on_task_completed(task_id, failed=False)
        pm = self.agents.get("pm")
        await self.broadcast_work({
            "type": "task_approved",
            "task_id": task_id,
            "agent_id": "pm",
            "agent_name": pm.name if pm else "Виктор",
            "agent_emoji": pm.emoji if pm else "🎯",
            "message": f"✅ **Виктор:** задача принята пользователем{f' — {note}' if note else ''}.",
            "timestamp": datetime.now().isoformat(),
        })
        await self._broadcast_task_history()
        return True

    async def request_task_revision(self, task_id: str, feedback: str) -> bool:
        t = self.task_history._find(task_id)
        if not t or t.get("status") != "awaiting_approval":
            return False
        self.task_history.mark_revision_requested(task_id, feedback)
        t["approval_notified"] = False
        self.task_history._save()

        revision_text = f"{t.get('task', '')}\n\n✎ Правки пользователя: {feedback}"
        pm = self.agents.get("pm")
        agent_id = t.get("agent_id")
        agent = self.agents.get(agent_id) if agent_id else None

        if pm and (t.get("target") == "all" or not agent):
            await pm.orchestrate_task(revision_text, self.agents, parent_id=task_id)
        elif agent:
            child_id = self.task_history.add_queued(
                revision_text, agent_id, agent.name, agent.emoji,
                parent_id=task_id, sender="Пользователь",
            )
            await agent.assign_task(
                revision_text, sender="Пользователь (правки)",
                parent_id=task_id, task_id=child_id,
            )
        await self.broadcast_work({
            "type": "task_revision",
            "task_id": task_id,
            "agent_id": "pm",
            "agent_name": pm.name if pm else "Виктор",
            "agent_emoji": pm.emoji if pm else "🎯",
            "message": f"✎ **Виктор:** отправил на доработку: {feedback[:200]}",
            "timestamp": datetime.now().isoformat(),
        })
        await self._broadcast_task_history()
        return True

    async def cancel_all_tasks(self, user_id: str = "", privileged: bool = False) -> int:
        """Отменить активные задачи (все — для admin, только свои — для пользователя)."""
        if privileged:
            count = self.task_history.cancel_all_active()
        else:
            count = self.task_history.cancel_active_for_user(user_id)
        for agent in self.agents.values():
            while not agent.task_queue.empty():
                try:
                    agent.task_queue.get_nowait()
                except Exception:
                    break
            if agent.status in ("working", "thinking"):
                agent.status = "idle"
                agent.location = "studio"
            agent.current_task = None
        await self.pipeline.clear()
        if count:
            await self.broadcast_work({
                "type": "system",
                "message": f"🛑 Отменено активных задач: {count}",
                "timestamp": datetime.now().isoformat(),
            })
        await self._broadcast_task_history()
        return count

    async def clear_task_history(self) -> int:
        """Полностью очистить журнал задач."""
        total = self.task_history.clear_all()
        for agent in self.agents.values():
            while not agent.task_queue.empty():
                try:
                    agent.task_queue.get_nowait()
                except Exception:
                    break
            agent.status = "idle"
            agent.location = "studio"
            agent.current_task = None
        await self.pipeline.clear()
        await self.broadcast_work({
            "type": "system",
            "message": "🗑️ История задач полностью очищена",
            "timestamp": datetime.now().isoformat(),
        })
        await self._broadcast_task_history()
        return total

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
