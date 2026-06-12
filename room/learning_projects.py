"""Учебные проекты, задания пользователя и оценки Маши."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import List, Optional

STORE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "learning_projects.json")
MAX_ITEMS = 300

AGENT_META = {
    "pm": ("🎯", "Виктор"),
    "architect": ("🏛️", "Алекс"),
    "backend": ("⚙️", "Макс"),
    "frontend": ("🎨", "Соня"),
    "qa": ("🧪", "Рита"),
    "reviewer": ("🔍", "Дэн"),
    "doc_writer": ("📝", "Лена"),
    "devops": ("🔧", "Кирилл"),
    "cursor": ("⚡", "Лео"),
    "presenter": ("📽️", "Ника"),
    "modeler": ("🧊", "Зоя"),
    "evaluator": ("🎓", "Маша"),
}


class LearningProjects:
    def __init__(self):
        self._load()

    def _load(self):
        if os.path.exists(STORE_FILE):
            try:
                with open(STORE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.projects: List[dict] = data.get("projects", [])
                self.evaluations: List[dict] = data.get("evaluations", [])
                return
            except Exception:
                pass
        self.projects = []
        self.evaluations = []

    def _save(self):
        os.makedirs(os.path.dirname(STORE_FILE), exist_ok=True)
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "projects": self.projects[-MAX_ITEMS:],
                "evaluations": self.evaluations[-MAX_ITEMS:],
                "updated_at": datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)

    def _new_id(self) -> str:
        return str(uuid.uuid4())[:10]

    def create_user_submission(
        self,
        title: str,
        description: str = "",
        collaborative: bool = False,
        cmd: str = "learn",
        target_agents: Optional[list] = None,
    ) -> dict:
        agents = target_agents or (["frontend", "backend", "qa"] if collaborative else ["frontend"])
        entry = {
            "id": self._new_id(),
            "kind": "collaborative" if collaborative else "user_exercise",
            "source": "user",
            "cmd": cmd,
            "title": (title or description or "Упражнение")[:120],
            "description": (description or title or "")[:800],
            "agent_ids": agents,
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }
        self.projects.insert(0, entry)
        self._save()
        return entry

    def create_agent_project(
        self,
        agent_id: str,
        title: str,
        summary: str = "",
        collaborative: bool = False,
        co_agent_ids: Optional[list] = None,
        topic: str = "",
    ) -> dict:
        co = co_agent_ids or []
        kind = "collaborative" if collaborative or len(co) > 0 else "solo"
        entry = {
            "id": self._new_id(),
            "kind": kind,
            "source": "agent",
            "title": (title or topic or "Проект")[:120],
            "description": (summary or "")[:800],
            "agent_ids": [agent_id] + [a for a in co if a != agent_id],
            "owner_agent_id": agent_id,
            "topic": topic[:80],
            "status": "active",
            "created_at": datetime.now().isoformat(),
        }
        self.projects.insert(0, entry)
        self._save()
        return entry

    def add_evaluation(
        self,
        agent_id: str,
        score: int,
        feedback: str,
        task: str = "",
        context: str = "learning",
        project_id: Optional[str] = None,
    ) -> dict:
        emoji, name = AGENT_META.get(agent_id, ("🤖", agent_id))
        ev = {
            "id": self._new_id(),
            "project_id": project_id,
            "agent_id": agent_id,
            "agent_name": name,
            "agent_emoji": emoji,
            "score": max(1, min(10, int(score))),
            "feedback": (feedback or "")[:600],
            "task": (task or "")[:200],
            "context": context,
            "created_at": datetime.now().isoformat(),
        }
        self.evaluations.insert(0, ev)
        if project_id:
            for p in self.projects:
                if p.get("id") == project_id:
                    p.setdefault("evaluations", []).append(ev["id"])
                    p["last_score"] = ev["score"]
                    break
        self._save()
        return ev

    def get_dashboard(self) -> dict:
        user_ex = [p for p in self.projects if p.get("source") == "user"]
        solo = [p for p in self.projects if p.get("kind") == "solo"]
        collab = [p for p in self.projects if p.get("kind") in ("collaborative",) or (
            p.get("kind") == "user_exercise" and len(p.get("agent_ids") or []) > 1
        )]
        avg = 0
        if self.evaluations:
            avg = round(sum(e.get("score", 0) for e in self.evaluations[:50]) / min(50, len(self.evaluations)), 1)
        evaluator = AGENT_META.get("evaluator", ("🎓", "Маша"))
        return {
            "stats": {
                "user_submissions": len(user_ex),
                "solo_projects": len(solo),
                "collaborative_projects": len(collab),
                "evaluations_count": len(self.evaluations),
                "average_score": avg,
            },
            "evaluator": {"agent_id": "evaluator", "emoji": evaluator[0], "name": evaluator[1]},
            "user_submissions": user_ex[:40],
            "solo_projects": solo[:40],
            "collaborative_projects": collab[:40],
            "evaluations": self.evaluations[:60],
            "projects": self.projects[:80],
        }

    def get_skill_matrix(self) -> dict:
        """Radar chart data — средние оценки по агентам."""
        scores: dict[str, list] = {}
        for ev in self.evaluations:
            aid = ev.get("agent_id", "unknown")
            scores.setdefault(aid, []).append(ev.get("score", 0))
        matrix = []
        for aid, vals in scores.items():
            emoji, name = AGENT_META.get(aid, ("🤖", aid))
            avg = round(sum(vals) / len(vals), 1) if vals else 0
            matrix.append({
                "agent_id": aid,
                "name": name,
                "emoji": emoji,
                "average": avg,
                "count": len(vals),
                "latest": vals[0] if vals else 0,
            })
        matrix.sort(key=lambda x: -x["average"])
        return {"agents": matrix, "total_evaluations": len(self.evaluations)}
