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
                    status: str = "queued", user_id: str = "",
                    user_name: str = "", task_kind: str = "") -> str:
        if parent_id and not user_id:
            parent = self._find(parent_id)
            if parent:
                user_id = parent.get("user_id", "")
                user_name = user_name or parent.get("user_name", "")
        task_id = str(uuid.uuid4())[:8]
        row = {
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
            "user_id": user_id or "",
            "user_name": user_name or "",
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "priority": "medium",
            "comments": [],
            "workspace_id": "",
        }
        if task_kind:
            row["task_kind"] = task_kind
        elif not parent_id and text:
            try:
                from room.task_routing import classify_task_kind
                kind = classify_task_kind(text)
                if kind != "generic":
                    row["task_kind"] = kind
            except Exception:
                pass
        self.tasks.append(row)
        self._save()
        return task_id

    def add_submitted(self, text: str, target: str, msg_type: str = "task",
                      user_id: str = "", user_name: str = "") -> str:
        return self.create_task(
            text, target, status="submitted",
            user_id=user_id, user_name=user_name,
        )

    def add_queued(self, text: str, agent_id: str, agent_name: str, agent_emoji: str,
                   parent_id: Optional[str] = None, sender: str = "",
                   user_id: str = "", user_name: str = "") -> str:
        return self.create_task(
            text, agent_id, agent_id=agent_id,
            agent_name=agent_name, agent_emoji=agent_emoji,
            parent_id=parent_id, sender=sender, status="queued",
            user_id=user_id, user_name=user_name,
        )

    def mark_in_progress(self, task_id: str):
        t = self._find(task_id)
        if t and t["status"] in ("queued", "submitted", "triaging", "revision_requested"):
            t["status"] = "in_progress"
            t["started_at"] = datetime.now().isoformat()
            self._save()

    def mark_awaiting_approval(self, task_id: str, response: str,
                               agent_name: str = "", agent_emoji: str = "",
                               artifact_id: str = None, preview_url: str = None,
                               download_url: str = None, artifact_type: str = None,
                               task_kind: str = None):
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
        if download_url:
            t["download_url"] = download_url
        if artifact_type:
            t["artifact_type"] = artifact_type
        if task_kind:
            t["task_kind"] = task_kind
        self._save()
        if t.get("parent_id"):
            self._try_complete_parent(t["parent_id"])

    @staticmethod
    def _pick_delivery_child(children: List[Dict]) -> Optional[Dict]:
        awaiting = [c for c in children if c.get("status") == "awaiting_approval"]
        if not awaiting:
            return None
        for agent_id in ("presenter", "modeler", "frontend", "doc_writer"):
            for c in awaiting:
                if c.get("agent_id") == agent_id:
                    return c
        return awaiting[0]

    def _bubble_delivery_to_parent(self, parent: Dict, children: List[Dict]) -> None:
        delivery = self._pick_delivery_child(children)
        if not delivery:
            return
        for key in ("artifact_id", "preview_url", "download_url", "artifact_type", "task_kind"):
            val = delivery.get(key)
            if val and not parent.get(key):
                parent[key] = val
        if delivery.get("agent_id"):
            parent["delivery_agent"] = delivery["agent_id"]

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
                self._bubble_delivery_to_parent(parent, children)
                self._save()
                return
            done = sum(1 for c in children if c.get("status") == "completed")
            parent["status"] = "completed"
            parent["completed_at"] = datetime.now().isoformat()
            parent["response"] = f"Выполнено {done}/{len(children)} подзадач команды"
            self._save()

    def get_all(self) -> List[Dict]:
        return self.enrich_for_ui(list(reversed(self.tasks)))

    def enrich_for_ui(self, tasks: List[Dict]) -> List[Dict]:
        """Родительским задачам подставляем ссылки на файл (pptx и т.д.) из подзадач."""
        by_id = {t.get("id"): dict(t) for t in tasks if t.get("id")}
        children_map: Dict[str, List[Dict]] = {}
        for t in tasks:
            pid = t.get("parent_id")
            if pid:
                children_map.setdefault(pid, []).append(t)

        out = []
        for t in tasks:
            row = dict(t)
            if not row.get("parent_id"):
                self._bubble_delivery_to_parent(row, children_map.get(row.get("id"), []))
                if not row.get("task_kind") and row.get("task"):
                    try:
                        from room.task_routing import classify_task_kind
                        kind = classify_task_kind(row["task"])
                        if kind != "generic":
                            row["task_kind"] = kind
                    except Exception:
                        pass
            out.append(row)
        return out

    def _belongs_to_user(self, task: dict, user_id: str) -> bool:
        if not user_id:
            return False
        tid = task.get("user_id") or ""
        if tid == user_id:
            return True
        pid = task.get("parent_id")
        if pid:
            parent = self._find(pid)
            if parent and parent.get("user_id") == user_id:
                return True
        return False

    def get_for_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        if not user_id:
            return []
        matched = [t for t in self.tasks if self._belongs_to_user(t, user_id)]
        return self.enrich_for_ui(list(reversed(matched)))[:limit]

    def stats_for_user(self, user_id: str) -> dict:
        tasks = [t for t in self.tasks if self._belongs_to_user(t, user_id)]
        completed = sum(1 for t in tasks if t.get("status") == "completed")
        active_statuses = (
            "submitted", "queued", "in_progress", "triaging",
            "awaiting_approval", "revision_requested",
        )
        active = sum(1 for t in tasks if t.get("status") in active_statuses)
        awaiting = sum(1 for t in tasks if t.get("status") == "awaiting_approval")
        failed = sum(1 for t in tasks if t.get("status") == "failed")
        cancelled = sum(1 for t in tasks if t.get("status") == "cancelled")
        return {
            "total": len(tasks),
            "completed": completed,
            "active": active,
            "awaiting_approval": awaiting,
            "failed": failed,
            "cancelled": cancelled,
        }

    def user_owns_task(self, task_id: str, user_id: str, privileged: bool = False) -> bool:
        if privileged:
            return True
        t = self._find(task_id)
        if not t:
            return False
        return self._belongs_to_user(t, user_id)

    def cancel_active_for_user(self, user_id: str) -> int:
        active = (
            "submitted", "queued", "in_progress", "triaging",
            "revision_requested", "awaiting_approval",
        )
        count = 0
        for t in self.tasks:
            if t.get("status") in active and self._belongs_to_user(t, user_id):
                t["status"] = "cancelled"
                t["completed_at"] = datetime.now().isoformat()
                count += 1
        if count:
            self._save()
        return count

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

    def find_active_duplicate(self, text: str, user_id: str = "") -> Optional[Dict]:
        """Есть ли уже такая задача в активных статусах (у того же пользователя)."""
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
            if user_id and not self._belongs_to_user(t, user_id):
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

    def _is_orphan(self, task: dict) -> bool:
        return not (task.get("user_id") or "").strip()

    def claim_orphans_for_user(
        self, user_id: str, email: str = "", name: str = ""
    ) -> int:
        """Привязать legacy-задачи без user_id по sender / user_name."""
        if not user_id:
            return 0
        email_l = (email or "").strip().lower()
        name_l = (name or "").strip().lower()
        count = 0
        for t in self.tasks:
            if not self._is_orphan(t):
                continue
            sender = (t.get("sender") or "").strip().lower()
            uname = (t.get("user_name") or "").strip().lower()
            matched = (
                (email_l and (sender == email_l or uname == email_l))
                or (name_l and name_l in (sender, uname))
            )
            if matched:
                t["user_id"] = user_id
                if name and not t.get("user_name"):
                    t["user_name"] = name
                count += 1
        if count:
            self._save()
        return count

    def assign_all_orphans_to(self, user_id: str, user_name: str = "") -> int:
        """Admin/owner: все задачи без user_id → указанный аккаунт."""
        if not user_id:
            return 0
        count = 0
        for t in self.tasks:
            if not self._is_orphan(t):
                continue
            t["user_id"] = user_id
            if user_name and not t.get("user_name"):
                t["user_name"] = user_name
            t.setdefault("legacy_migrated", True)
            count += 1
        if count:
            self._save()
        return count

    def orphan_count(self) -> int:
        return sum(1 for t in self.tasks if self._is_orphan(t))

    def add_comment(
        self,
        task_id: str,
        text: str,
        user_id: str = "",
        user_name: str = "User",
    ) -> Optional[Dict]:
        t = self._find(task_id)
        if not t or not text.strip():
            return None
        comment = {
            "id": str(uuid.uuid4())[:8],
            "text": text.strip()[:500],
            "user_id": user_id,
            "user_name": user_name[:60],
            "created_at": datetime.now().isoformat(),
        }
        t.setdefault("comments", []).append(comment)
        self._save()
        return comment

    def get_comments(self, task_id: str) -> list:
        t = self._find(task_id)
        return list(t.get("comments", [])) if t else []
