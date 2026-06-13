import json
import os
from typing import List, Dict

KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), "knowledge")
MAX_STORED_TOPICS = 100


class KnowledgeStore:
    """Персистентное хранилище знаний агентов между перезапусками."""

    @staticmethod
    def _path(agent_id: str) -> str:
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        return os.path.join(KNOWLEDGE_DIR, f"{agent_id}.json")

    @staticmethod
    def load(agent_id: str) -> List[Dict]:
        path = KnowledgeStore._path(agent_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def save(agent_id: str, topics: List[Dict]) -> None:
        path = KnowledgeStore._path(agent_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(topics[-MAX_STORED_TOPICS:], f, indent=2, ensure_ascii=False)
        try:
            from integrations.knowledge_sync import mark_knowledge_dirty
            mark_knowledge_dirty()
        except Exception:
            pass
