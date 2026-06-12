import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "data", "task_history.json")
MAX_TASKS = 500


class TaskHistory:
    """Журнал задач с надёжным отслеживанием статусов."""

    def __init__(self):
        self.tasks: List[Dict] = []
        self._load()

    def _load(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = data if isinstance(data, list) else []
            except Exception:
                self.tasks = []

    def _save(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks[-MAX_TASKS:], f, indent=2, ensure_ascii=False)

    def _find(self, task_id: str) -> Optional[Dict]:
        for t in self.tasks:
            if t.get("id") == task_id:
                return t
        return None

    def create_task(self, text: str, target: str, agent_id: str = None,
                    agent_name: str = None, agent_emoji: str = None,
                    parent_id: str = None, sender: str = "",
                    status: str = "queued") -> str:
        task_id = str(uuid.uuid4())[:8]
        self.tasks.append({
            "id": task_id,
            "task": text,
            "target": target,
            "status": status,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "agent_emoji": agent_emoji,
            "response": None,
            "parent_id": parent_id,
            "sender": sender,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "priority": "medium",
        })
        self._save()
        return task_id

    def add_submitted(self, text: str, target: str, msg_type: str = "task") -> str:
        return self.create_task(text, target, status="submitted")

    def add_queued(self, text: str, agent_id: str, agent_name: str, agent_emoji: str,
                   parent_id: Optional[str] = None, sender: str = "") -> str:
        return self.create_task(
            text, agent_id, agent_id=agent_id,
            agent_name=agent_name, agent_emoji=agent_emoji,
            parent_id=parent_id, sender=sender, status="queued"
        )

    def mark_in_progress(self, task_id: str):
        t = self._find(task_id)
        if t and t["status"] in ("queued", "submitted", "triaging", "revision_requested"):
            t["status"] = "in_progress"
            t["started_at"] = datetime.now().isoformat()
            self._save()

    def mark_awaiting_approval(self, task_id: str, response: str,
                               agent_name: str = "", agent_emoji: str = "",
                               artifact_id: str = None, preview_url: str = None):
        t = self._find(task_id)
        if not t:
            return
        t["status"] = "awaiting_approval"
        t["response"] = (response or "")[:2000]
        t["awaiting_since"] = datetime.now().isoformat()
        if agent_name:
            t["agent_name"] = agent_name
        if agent_emoji:
            t["agent_emoji"] = agent_emoji
        if artifact_id:
            t["artifact_id"] = artifact_id
        if preview_url:
            t["preview_url"] = preview_url
        self._save()
        if t.get("parent_id"):
            self._try_complete_parent(t["parent_id"])

    def mark_user_approved(self, task_id: str, user_note: str = ""):
        t = self._find(task_id)
        if not t:
            return False
        now = datetime.now().isoformat()
        for child in self.tasks:
            if child.get("parent_id") == task_id and child.get("status") == "awaiting_approval":
                child["status"] = "completed"
                child["completed_at"] = now
                child["user_approved"] = True
        t["status"] = "completed"
        t["completed_at"] = now
        t["user_approved"] = True
        if user_note:
            t["user_note"] = user_note[:500]
        self._save()
        if t.get("parent_id"):
            self._try_complete_parent(t["parent_id"])
        return True

    def mark_revision_requested(self, task_id: str, feedback: str = ""):
        t = self._find(task_id)
        if not t:
            return False
        t["status"] = "revision_requested"
        t["revision_feedback"] = (feedback or "")[:1000]
        t["revision_count"] = int(t.get("revision_count") or 0) + 1
        self._save()
        return True

    def mark_completed(self, task_id: str, response: str,
                       agent_name: str = "", agent_emoji: str = ""):
        t = self._find(task_id)
        if not t:
            return
        t["status"] = "completed"
        t["response"] = (response or "")[:2000]
        t["completed_at"] = datetime.now().isoformat()
        if agent_name:
            t["agent_name"] = agent_name
        if agent_emoji:
            t["agent_emoji"] = agent_emoji
        self._save()
        if t.get("parent_id"):
            self._try_complete_parent(t["parent_id"])

    def mark_failed(self, task_id: str, error: str = ""):
        t = self._find(task_id)
        if not t:
            return
        t["status"] = "failed"
        t["response"] = error[:500] if error else "Ошибка выполнения"
        t["completed_at"] = datetime.now().isoformat()
        self._save()

    def _try_complete_parent(self, parent_id: str):
        parent = self._find(parent_id)
        if not parent:
            return
        children = [t for t in self.tasks if t.get("parent_id") == parent_id]
        if not children:
            return
        if all(c.get("status") in ("completed", "failed", "awaiting_approval") for c in children):
            if any(c.get("status") == "awaiting_approval" for c in children):
                parent["status"] = "awaiting_approval"
                self._save()
                return
            done = sum(1 for c in children if c.get("status") == "completed")
            parent["status"] = "completed"
            parent["completed_at"] = datetime.now().isoformat()
            parent["response"] = f"Выполнено {done}/{len(children)} подзадач команды"
            self._save()

    def get_all(self) -> List[Dict]:
        return list(reversed(self.tasks))

    def get_completed(self) -> List[Dict]:
        return [t for t in reversed(self.tasks) if t.get("status") == "completed"]

    def get_active(self) -> List[Dict]:
        active_statuses = (
            "submitted", "queued", "in_progress", "triaging",
            "awaiting_approval", "revision_requested",
        )
        return [t for t in reversed(self.tasks) if t.get("status") in active_statuses]

    def stats(self) -> dict:
        completed = sum(1 for t in self.tasks if t.get("status") == "completed")
        active_statuses = (
            "submitted", "queued", "in_progress", "triaging",
            "awaiting_approval", "revision_requested",
        )
        active = sum(1 for t in self.tasks if t.get("status") in active_statuses)
        awaiting = sum(1 for t in self.tasks if t.get("status") == "awaiting_approval")
        failed = sum(1 for t in self.tasks if t.get("status") == "failed")
        cancelled = sum(1 for t in self.tasks if t.get("status") == "cancelled")
        return {
            "total": len(self.tasks),
            "completed": completed,
            "active": active,
            "awaiting_approval": awaiting,
            "failed": failed,
            "cancelled": cancelled,
        }

    def _normalize_task_text(self, text: str) -> str:
        return (text or "").strip().lower()[:120]

    def find_active_duplicate(self, text: str) -> Optional[Dict]:
        """Есть ли уже такая задача в активных статусах."""
        norm = self._normalize_task_text(text)
        if not norm:
            return None
        active = (
            "submitted", "queued", "in_progress", "triaging",
            "revision_requested", "awaiting_approval",
        )
        for t in reversed(self.tasks):
            if t.get("status") not in active:
                continue
            if self._normalize_task_text(t.get("task", "")) == norm:
                return t
        return None

    def cleanup_stale(self, max_minutes: int = 30):
        """Помечает зависшие in_progress и submitted задачи как cancelled."""
        from datetime import timedelta
        now = datetime.now()
        changed = False
        for t in self.tasks:
            status = t.get("status")
            if status not in ("in_progress", "submitted"):
                continue
            started = t.get("started_at") or t.get("created_at")
            if not started:
                continue
            try:
                started_dt = datetime.fromisoformat(started)
            except ValueError:
                continue
            limit = max_minutes if status == "in_progress" else min(max_minutes, 20)
            if now - started_dt > timedelta(minutes=limit):
                t["status"] = "cancelled"
                t["response"] = (
                    "Таймаут (задача зависла)" if status == "in_progress"
                    else "Отменено — задача не была обработана"
                )
                t["completed_at"] = now.isoformat()
                changed = True
                if t.get("parent_id"):
                    self._try_complete_parent(t["parent_id"])
        if changed:
            self._save()

    def set_priority(self, task_id: str, priority: str) -> bool:
        t = self._find(task_id)
        if not t:
            return False
        if priority not in ("urgent", "high", "medium", "low"):
            priority = "medium"
        t["priority"] = priority
        self._save()
        return True

    def cancel_all_active(self) -> int:
        """Отменить все незавершённые задачи."""
        active = (
            "submitted", "queued", "in_progress", "triaging",
            "revision_requested", "awaiting_approval",
        )
        now = datetime.now().isoformat()
        count = 0
        for t in self.tasks:
            if t.get("status") not in active:
                continue
            t["status"] = "cancelled"
            t["completed_at"] = now
            t["response"] = "Отменено пользователем"
            count += 1
        if count:
            self._save()
        return count

    def clear_all(self) -> int:
        """Полностью очистить журнал задач."""
        total = len(self.tasks)
        self.tasks = []
        self._save()
        return total
