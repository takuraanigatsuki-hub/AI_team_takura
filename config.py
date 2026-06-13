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
    "cursor_github_sync": False,
    "github_sync_on_tasks": False,
    "cursor_auto_create_pr": True,
    "git_auto_sync": True,
    "git_sync_interval_sec": 60,
    "m365_enabled": True,
    "figma_access_token": "",
    "figma_client_id": "",
    "figma_client_secret": "",
    "figma_redirect_uri": "",
    "figma_default_url": "",
    "figma_study_enabled": True,
    "figma_study_interval_min": 12,
    "figma_study_interval_max": 25,
    "figma_api_min_interval_sec": 2.5,
    "figma_rate_limit_cooldown_sec": 120,
    "figma_rate_limit_max_cooldown_sec": 600,
    "figma_reference_urls": [],
    "figma_auto_discover": True,
    "figma_discover_team_files": True,
    "figma_discovery_catalog": [],
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "llm_model": "gpt-4o-mini",
    "llm_router_model": "gpt-4o-mini",
    "embedding_model": "text-embedding-3-small",
    "evaluator_min_score": 6,
    "rag_hybrid": True,
    "room_api_key": "",
    "auto_theme": False,
    "telegram_notify_tasks": False,
    "telegram_notify_studio": True,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "stripe_secret_key": "",
    "stripe_webhook_secret": "",
    "stripe_price_starter": "",
    "stripe_price_pro": "",
    "stripe_price_team": "",
    "jira_auto_create": False,
    "jira_url": "",
    "jira_token": "",
    "jira_email": "",
    "jira_project": "PROJ",
    "linear_auto_create": False,
    "linear_api_key": "",
    "linear_team_id": "",
    "notion_token": "",
    "notion_parent_page_id": "",
    "vercel_token": "",
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
    cfg["figma_client_id"] = os.environ.get("FIGMA_CLIENT_ID") or cfg.get("figma_client_id") or ""
    cfg["figma_client_secret"] = os.environ.get("FIGMA_CLIENT_SECRET") or cfg.get("figma_client_secret") or ""
    cfg["figma_redirect_uri"] = os.environ.get("FIGMA_REDIRECT_URI") or cfg.get("figma_redirect_uri") or ""
    cfg["openai_api_key"] = os.environ.get("OPENAI_API_KEY") or cfg.get("openai_api_key") or ""
    cfg["openai_base_url"] = os.environ.get("OPENAI_BASE_URL") or cfg.get("openai_base_url") or "https://api.openai.com/v1"
    cfg["llm_model"] = os.environ.get("LLM_MODEL") or cfg.get("llm_model") or "gpt-4o-mini"
    cfg["llm_router_model"] = os.environ.get("LLM_ROUTER_MODEL") or cfg.get("llm_router_model") or cfg["llm_model"]
    cfg["embedding_model"] = os.environ.get("EMBEDDING_MODEL") or cfg.get("embedding_model") or "text-embedding-3-small"
    cfg["evaluator_min_score"] = int(os.environ.get("EVALUATOR_MIN_SCORE") or cfg.get("evaluator_min_score") or 6)
    rag_hybrid = os.environ.get("RAG_HYBRID", "")
    if rag_hybrid.lower() in ("0", "false", "no"):
        cfg["rag_hybrid"] = False
    elif rag_hybrid:
        cfg["rag_hybrid"] = True
    cfg["room_api_key"] = os.environ.get("ROOM_API_KEY") or cfg.get("room_api_key") or ""
    for key, env in (
        ("telegram_bot_token", "TELEGRAM_BOT_TOKEN"),
        ("telegram_chat_id", "TELEGRAM_CHAT_ID"),
        ("jira_url", "JIRA_URL"),
        ("jira_token", "JIRA_TOKEN"),
        ("jira_email", "JIRA_EMAIL"),
        ("linear_api_key", "LINEAR_API_KEY"),
        ("linear_team_id", "LINEAR_TEAM_ID"),
        ("notion_token", "NOTION_TOKEN"),
        ("notion_parent_page_id", "NOTION_PARENT_PAGE_ID"),
        ("vercel_token", "VERCEL_TOKEN"),
    ):
        cfg[key] = os.environ.get(env) or cfg.get(key) or ""
    return cfg


config = _load_config()
