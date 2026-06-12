import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")

_defaults = {
    "host": "0.0.0.0",
    "port": 8000,
    "learning_interval_min": 15,
    "learning_interval_max": 45,
    "learning_sources": ["devto", "hackernews"],
    "persist_knowledge": True,
    "debug": False,
    "cursor_api_key": "",
    "cursor_enabled": False,
    "cursor_model": "composer-2.5",
    "cursor_repo_url": "https://github.com/takuraanigatsuki-hub/AI_team_takura",
    "cursor_repo_ref": "main",
    "cursor_cloud_mode": True,
    "cursor_github_sync": True,
    "cursor_auto_create_pr": True,
    "git_auto_sync": True,
    "git_sync_interval_sec": 60,
    "figma_access_token": "",
    "figma_default_url": "https://www.figma.com/site/uYRfrETGR8pcwChwLtJ6Ua/Untitled?t=S7zOAy3vHRn3HWqR-0",
}


def _load_dotenv() -> None:
    """Загружает переменные из .env без внешних зависимостей."""
    if not os.path.exists(ENV_FILE):
        return
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception:
        pass


def _load_config() -> dict:
    _load_dotenv()
    cfg = _defaults.copy()
    file_data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                cfg.update(file_data)
        except Exception:
            pass
    cursor_key = os.environ.get("CURSOR_API_KEY") or cfg.get("cursor_api_key") or ""
    cfg["cursor_api_key"] = cursor_key
    repo_env = os.environ.get("CURSOR_REPO_URL", "").strip()
    if repo_env and not cfg.get("cursor_repo_url"):
        cfg["cursor_repo_url"] = repo_env
    if cursor_key:
        cfg["cursor_enabled"] = file_data.get("cursor_enabled", True)
    else:
        cfg["cursor_enabled"] = False
    figma_token = os.environ.get("FIGMA_ACCESS_TOKEN") or cfg.get("figma_access_token") or ""
    cfg["figma_access_token"] = figma_token
    return cfg


config = _load_config()
