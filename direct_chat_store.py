import json
import os
from typing import List, Dict

CHAT_DIR = os.path.join(os.path.dirname(__file__), "direct_chats")
MAX_MESSAGES = 200


class DirectChatStore:
    @staticmethod
    def _path(agent_id: str) -> str:
        os.makedirs(CHAT_DIR, exist_ok=True)
        return os.path.join(CHAT_DIR, f"{agent_id}.json")

    @staticmethod
    def load(agent_id: str) -> List[Dict]:
        path = DirectChatStore._path(agent_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []

    @staticmethod
    def save(agent_id: str, messages: List[Dict]) -> None:
        with open(DirectChatStore._path(agent_id), "w", encoding="utf-8") as f:
            json.dump(messages[-MAX_MESSAGES:], f, indent=2, ensure_ascii=False)
