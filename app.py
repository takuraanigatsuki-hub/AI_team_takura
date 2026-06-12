import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from pydantic import BaseModel

from room.room_manager import RoomManager
from agents import (
    ArchitectAgent, BackendDevAgent, FrontendDevAgent,
    QATesterAgent, CodeReviewerAgent, DocWriterAgent,
    DevOpsAgent, PMOrchestratorAgent, CursorAgent
)

# Глобальный менеджер комнаты
room = RoomManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация при запуске"""
    # Создаём агентов
    agents = [
        PMOrchestratorAgent(room),
        ArchitectAgent(room),
        BackendDevAgent(room),
        FrontendDevAgent(room),
        QATesterAgent(room),
        CodeReviewerAgent(room),
        DocWriterAgent(room),
        DevOpsAgent(room),
        CursorAgent(room),
    ]

    # Регистрируем всех агентов
    for agent in agents:
        room.register_agent(agent)

    room.task_history.cleanup_stale(max_minutes=30)

    # Запускаем агентов
    await room.start_all_agents()

    # Запускаем периодическую рассылку состояния
    state_task = asyncio.create_task(room.state_broadcaster())

    from integrations.github_sync import cloud_agent_poller
    github_poll_task = asyncio.create_task(cloud_agent_poller(room))

    import config as cfg_module
    if cfg_module.config.get("cursor_github_sync"):
        print("🔗 GitHub Sync: включён (Cursor Cloud Agent)")
        repo = cfg_module.config.get("cursor_repo_url") or "(авто из Cursor API)"
        print(f"   Repo: {repo}")

        try:
            from integrations.github_sync import resolve_repo_url
            resolved = await resolve_repo_url()
            if resolved and resolved != cfg_module.config.get("cursor_repo_url"):
                cfg_module.config["cursor_repo_url"] = resolved
                config_file = os.path.join(os.path.dirname(__file__), "config.json")
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        current = json.load(f)
                    current["cursor_repo_url"] = resolved
                    with open(config_file, "w", encoding="utf-8") as f:
                        json.dump(current, f, indent=4, ensure_ascii=False)
                    print(f"   Repo (из Cursor API): {resolved}")
                except Exception:
                    pass
            elif resolved:
                print(f"   Repo: {resolved}")
        except Exception as e:
            print(f"   ⚠️ Repo resolve: {e}")

    from integrations.local_git_sync import auto_sync_loop, sync_changes_async
    git_interval = cfg_module.config.get("git_sync_interval_sec", 60)
    git_sync_task = asyncio.create_task(auto_sync_loop(room, interval=git_interval))

    if cfg_module.config.get("git_auto_sync", True):
        print("📤 Git Auto-Sync: включён (commit + push каждые "
              f"{git_interval}с при изменениях)")
        try:
            boot = await sync_changes_async("auto: startup sync")
            if boot.get("action") == "pushed":
                print(f"   Pushed: {boot.get('commit')} → origin/{boot.get('branch')}")
        except Exception as e:
            print(f"   ⚠️ Startup git sync: {e}")

    print("🚀 AI Team Room запущен!")
    print("📡 Открой браузер: http://localhost:8000")

    yield  # Приложение работает

    # Остановка
    state_task.cancel()
    github_poll_task.cancel()
    git_sync_task.cancel()
    try:
        from integrations.local_git_sync import sync_changes_async
        import config as cfg_module
        if cfg_module.config.get("git_auto_sync", True):
            await sync_changes_async("auto: shutdown sync")
    except Exception:
        pass
    await room.stop_all_agents()
    print("👋 AI Team Room остановлен")


app = FastAPI(
    title="AI Team Room",
    description="Комната с командой ИИ-агентов",
    version="1.0.0",
    lifespan=lifespan
)

# Подключаем статику
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─── REST API ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Главная страница"""
    html_file = os.path.join(static_dir, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Static files not found</h1>")


@app.get("/api/agents")
async def get_agents():
    """Получить состояние всех агентов"""
    return {
        "agents": [agent.get_state() for agent in room.agents.values()]
    }


@app.get("/api/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Получить состояние конкретного агента"""
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return agent.get_state()


@app.get("/api/agents/{agent_id}/history")
async def get_agent_history(agent_id: str):
    """Получить историю сообщений агента"""
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return {"messages": agent.messages_log}


@app.get("/api/agents/{agent_id}/knowledge")
async def get_agent_knowledge(agent_id: str):
    """Получить знания агента"""
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return {"learned_topics": agent.learned_topics}


@app.get("/api/agents/frontend/preview")
async def get_frontend_preview():
    """Последний React preview от Сони"""
    agent = room.agents.get("frontend")
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    if not getattr(agent, "last_preview", None):
        return {"preview": None}
    return {"preview": agent.last_preview}


class TaskRequest(BaseModel):
    text: str
    target: str = "all"


@app.post("/api/task")
async def assign_task(request: TaskRequest):
    """Назначить задачу через REST API"""
    await room.handle_user_message({
        "type": "task",
        "text": request.text,
        "target": request.target
    })
    return {"status": "ok", "message": f"Задача назначена: {request.text}"}


@app.get("/api/agents/{agent_id}/direct-chat")
async def get_direct_chat(agent_id: str):
    """Личная переписка с агентом"""
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    return {"messages": agent.direct_chat}


class DirectChatRequest(BaseModel):
    text: str


@app.post("/api/agents/{agent_id}/direct-chat")
async def send_direct_chat(agent_id: str, request: DirectChatRequest):
    """Отправить личное сообщение агенту"""
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    await agent.handle_direct_chat(request.text)
    return {"status": "ok", "messages": agent.direct_chat[-4:]}


class ConfigUpdate(BaseModel):
    learning_interval_min: int = None
    learning_interval_max: int = None
    persist_knowledge: bool = None
    cursor_repo_url: str = None
    cursor_repo_ref: str = None
    cursor_enabled: bool = None
    cursor_github_sync: bool = None
    cursor_cloud_mode: bool = None
    cursor_auto_create_pr: bool = None
    git_auto_sync: bool = None
    git_sync_interval_sec: int = None


class CursorRunRequest(BaseModel):
    prompt: str
    repo_url: str = ""


class FigmaImportRequest(BaseModel):
    url: str


@app.get("/api/config")
async def get_config():
    """Текущая конфигурация обучения"""
    import config as cfg_module
    return {
        "learning_interval_min": cfg_module.config.get("learning_interval_min", 15),
        "learning_interval_max": cfg_module.config.get("learning_interval_max", 45),
        "learning_sources": cfg_module.config.get("learning_sources", [
            "web_search", "wikipedia", "devto", "github", "habr",
            "stackoverflow", "hackernews", "books", "arxiv", "gutenberg"
        ]),
        "persist_knowledge": cfg_module.config.get("persist_knowledge", True),
        "cursor_enabled": cfg_module.config.get("cursor_enabled", False),
        "cursor_model": cfg_module.config.get("cursor_model", "composer-2.5"),
        "cursor_repo_url": cfg_module.config.get("cursor_repo_url", ""),
        "cursor_repo_ref": cfg_module.config.get("cursor_repo_ref", "main"),
        "cursor_github_sync": cfg_module.config.get("cursor_github_sync", False),
        "cursor_cloud_mode": cfg_module.config.get("cursor_cloud_mode", True),
        "cursor_auto_create_pr": cfg_module.config.get("cursor_auto_create_pr", True),
        "figma_configured": bool(cfg_module.config.get("figma_access_token")),
        "figma_default_url": cfg_module.config.get("figma_default_url", ""),
        "git_auto_sync": cfg_module.config.get("git_auto_sync", True),
        "git_sync_interval_sec": cfg_module.config.get("git_sync_interval_sec", 60),
    }


@app.post("/api/config")
async def update_config(update: ConfigUpdate):
    """Обновить настройки самообучения"""
    import config as cfg_module

    config_file = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            current = json.load(f)
    except Exception:
        current = {}

    if update.learning_interval_min is not None:
        current["learning_interval_min"] = max(5, update.learning_interval_min)
        cfg_module.config["learning_interval_min"] = current["learning_interval_min"]

    if update.learning_interval_max is not None:
        current["learning_interval_max"] = max(10, update.learning_interval_max)
        cfg_module.config["learning_interval_max"] = current["learning_interval_max"]

    if update.persist_knowledge is not None:
        current["persist_knowledge"] = update.persist_knowledge
        cfg_module.config["persist_knowledge"] = update.persist_knowledge

    if update.cursor_repo_url is not None:
        current["cursor_repo_url"] = update.cursor_repo_url.strip()
        cfg_module.config["cursor_repo_url"] = current["cursor_repo_url"]

    if update.cursor_repo_ref is not None:
        current["cursor_repo_ref"] = update.cursor_repo_ref.strip() or "main"
        cfg_module.config["cursor_repo_ref"] = current["cursor_repo_ref"]

    if update.cursor_enabled is not None:
        current["cursor_enabled"] = update.cursor_enabled
        cfg_module.config["cursor_enabled"] = update.cursor_enabled and bool(cfg_module.config.get("cursor_api_key"))

    if update.cursor_github_sync is not None:
        current["cursor_github_sync"] = update.cursor_github_sync
        cfg_module.config["cursor_github_sync"] = update.cursor_github_sync

    if update.cursor_cloud_mode is not None:
        current["cursor_cloud_mode"] = update.cursor_cloud_mode
        cfg_module.config["cursor_cloud_mode"] = update.cursor_cloud_mode

    if update.cursor_auto_create_pr is not None:
        current["cursor_auto_create_pr"] = update.cursor_auto_create_pr
        cfg_module.config["cursor_auto_create_pr"] = update.cursor_auto_create_pr

    if update.git_auto_sync is not None:
        current["git_auto_sync"] = update.git_auto_sync
        cfg_module.config["git_auto_sync"] = update.git_auto_sync

    if update.git_sync_interval_sec is not None:
        current["git_sync_interval_sec"] = max(30, update.git_sync_interval_sec)
        cfg_module.config["git_sync_interval_sec"] = current["git_sync_interval_sec"]

    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=4, ensure_ascii=False)

    return {"status": "ok", "message": "Настройки обучения обновлены"}


@app.get("/api/knowledge/stats")
async def get_knowledge_stats():
    """Статистика базы знаний всех агентов"""
    return {
        "agents": [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "learned_count": len(agent.learned_topics),
                "sources": list(dict.fromkeys(
                    t.get("source", "") for t in agent.learned_topics if t.get("source")
                )),
            }
            for agent in room.agents.values()
        ]
    }


@app.get("/api/history")
async def get_history():
    """Получить историю сообщений комнаты"""
    return {
        "work": room.work_history,
        "learning": room.learning_history,
    }


@app.get("/api/sites/latest")
async def get_latest_site():
    """Готовый HTML-сайт от Сони"""
    site_file = os.path.join(os.path.dirname(__file__), "output", "sites", "latest.html")
    if os.path.exists(site_file):
        return FileResponse(site_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Сайт ещё не создан. Дайте Соне задачу со словом «сайт».")


@app.get("/api/tasks")
async def get_tasks():
    """Журнал задач: все, выполненные, активные"""
    return {
        "stats": room.task_history.stats(),
        "tasks": room.task_history.get_all()[:100],
        "completed": room.task_history.get_completed()[:50],
        "active": room.task_history.get_active()[:30],
    }


@app.get("/api/dashboard")
async def get_dashboard():
    """Сводка для Dashboard: команда, знания, интеграции."""
    import config as cfg_module
    from integrations.local_git_sync import get_status as git_status

    agents_data = []
    total_knowledge = 0
    for agent in room.agents.values():
        state = agent.get_state()
        agents_data.append({
            "agent_id": agent.agent_id,
            "name": agent.name,
            "emoji": agent.emoji,
            "status": agent.status,
            "learned_count": len(agent.learned_topics),
            "role": agent.role,
        })
        total_knowledge += len(agent.learned_topics)

    git = git_status()
    return {
        "team_size": len(room.agents),
        "agents": agents_data,
        "total_knowledge": total_knowledge,
        "task_stats": room.task_history.stats(),
        "figma_configured": bool(cfg_module.config.get("figma_access_token")),
        "git_auto_sync": cfg_module.config.get("git_auto_sync", True),
        "cursor_enabled": cfg_module.config.get("cursor_enabled", False),
        "cursor_repo_url": cfg_module.config.get("cursor_repo_url", ""),
        "git": git,
    }


# ─── Git Auto-Sync ────────────────────────────────────────────

@app.get("/api/git/status")
async def git_status():
    from integrations.local_git_sync import get_status
    return get_status()


@app.post("/api/git/sync")
async def git_sync_now():
    """Немедленный commit + push в GitHub."""
    from integrations.local_git_sync import sync_changes_async
    result = await sync_changes_async("manual: sync from API")
    if not result.get("ok") and result.get("action") not in ("skip",):
        raise HTTPException(status_code=500, detail=result.get("error", "Git sync failed"))
    if result.get("action") == "pushed":
        await room.broadcast_work({
            "type": "git_sync_done",
            "message": f"📤 GitHub: `{result.get('commit')}` → {result.get('branch')}",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
    return result


# ─── Cursor SDK ─────────────────────────────────────────────

@app.get("/api/cursor/status")
async def cursor_status():
    """Проверка Cursor API ключа и последних runs."""
    import config as cfg_module
    from integrations.cursor_client import get_client, cursor_runs
    from integrations.github_sync import active_cloud_agents, resolve_repo_url

    if not cfg_module.config.get("cursor_enabled"):
        return {"ok": False, "configured": False, "message": "CURSOR_API_KEY не задан"}

    client = get_client()
    verify = await client.verify_key()
    repos = await client.list_repositories() if verify.get("ok") else []
    resolved_repo = await resolve_repo_url()
    recent = list(cursor_runs.values())[-10:][::-1]
    return {
        "ok": verify.get("ok", False),
        "configured": True,
        "model": cfg_module.config.get("cursor_model"),
        "repo_url": resolved_repo or cfg_module.config.get("cursor_repo_url", ""),
        "github_sync": cfg_module.config.get("cursor_github_sync", False),
        "cloud_mode": cfg_module.config.get("cursor_cloud_mode", True),
        "auto_create_pr": cfg_module.config.get("cursor_auto_create_pr", True),
        "active_agents": list(active_cloud_agents.keys()),
        "user": verify.get("user"),
        "error": verify.get("error"),
        "repositories": repos[:20],
        "recent_runs": recent,
    }


@app.post("/api/cursor/run")
async def cursor_run(request: CursorRunRequest):
    """Запуск Cursor Agent (локально или cloud)."""
    import config as cfg_module
    from integrations.cursor_client import get_client

    if not cfg_module.config.get("cursor_enabled"):
        raise HTTPException(status_code=400, detail="Cursor SDK не настроен")

    client = get_client()
    repo = request.repo_url or await __import__(
        "integrations.github_sync", fromlist=["resolve_repo_url"]
    ).resolve_repo_url()
    run = await client.run_task(
        prompt=request.prompt,
        repo_url=repo,
        ref=cfg_module.config.get("cursor_repo_ref", "main"),
        auto_create_pr=cfg_module.config.get("cursor_auto_create_pr", True),
        force_cloud=bool(repo),
    )
    agent_id = run.get("agent_id")
    if agent_id:
        from integrations.github_sync import active_cloud_agents
        active_cloud_agents[agent_id] = {
            "run_id": run.get("id"),
            "prompt": request.prompt[:500],
            "repo_url": repo,
            "started_at": run.get("started_at"),
        }
    await room.broadcast_work({
        "type": "cursor_run_done",
        "run_id": run.get("id"),
        "mode": run.get("mode"),
        "status": run.get("status"),
        "agent_name": "Лео",
        "agent_emoji": "⚡",
        "message": run.get("text", "")[:2000],
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    })
    return run


@app.get("/api/cursor/runs/{run_id}")
async def cursor_run_status(run_id: str):
    from integrations.cursor_client import cursor_runs

    run = cursor_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run не найден")
    return run


@app.get("/api/cursor/repositories")
async def cursor_repositories():
    """Список GitHub-репозиториев из Cursor Dashboard."""
    import config as cfg_module
    from integrations.cursor_client import get_client

    if not cfg_module.config.get("cursor_enabled"):
        raise HTTPException(status_code=400, detail="Cursor SDK не настроен")
    client = get_client()
    repos = await client.list_repositories()
    return {"repositories": repos}


@app.post("/api/cursor/sync")
async def cursor_github_sync(request: CursorRunRequest):
    """Ручной запуск синхронизации задачи с GitHub."""
    import config as cfg_module
    from integrations.github_sync import sync_task_to_github

    if not cfg_module.config.get("cursor_enabled"):
        raise HTTPException(status_code=400, detail="Cursor SDK не настроен")
    run = await sync_task_to_github(request.prompt, room_manager=room, source="manual")
    if not run:
        raise HTTPException(status_code=400, detail="GitHub Sync не настроен или нет repo")
    return run


# ─── Figma ────────────────────────────────────────────────────

@app.post("/api/figma/import")
async def figma_import(request: FigmaImportRequest):
    """Импорт макета из Figma по URL."""
    from integrations.figma_client import get_client, parse_figma_url

    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL обязателен")
    parsed = parse_figma_url(request.url)
    if not parsed:
        raise HTTPException(status_code=400, detail="Некорректная ссылка Figma")

    client = get_client()
    if not client.configured:
        raise HTTPException(
            status_code=400,
            detail="FIGMA_ACCESS_TOKEN не задан. Добавьте в .env",
        )
    try:
        result = await client.import_design(request.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    frontend = room.agents.get("frontend")
    if frontend and hasattr(frontend, "apply_figma_design"):
        await frontend.apply_figma_design(result)

    await room.broadcast_work({
        "type": "figma_import",
        "title": result["summary"].get("file_name", "Figma"),
        "colors": result["summary"].get("colors", []),
        "preview_url": result.get("preview_url"),
        "css_tokens": result.get("css_tokens"),
        "url": request.url,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    })
    return result


@app.get("/api/figma/parse")
async def figma_parse(url: str):
    from integrations.figma_client import parse_figma_url

    parsed = parse_figma_url(url)
    if not parsed:
        raise HTTPException(status_code=400, detail="Некорректная ссылка")
    return parsed


# ─── WebSocket ──────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket соединение для реального времени"""
    await room.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await room.handle_user_message(message)
            except json.JSONDecodeError:
                # Если просто текст — считаем как задачу всем
                await room.handle_user_message({
                    "type": "task",
                    "text": data,
                    "target": "all"
                })
    except WebSocketDisconnect:
        await room.disconnect(websocket)
    except Exception as e:
        await room.disconnect(websocket)
