import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from pydantic import BaseModel

from room.room_manager import RoomManager
from agents import (
    ArchitectAgent, BackendDevAgent, FrontendDevAgent,
    QATesterAgent, CodeReviewerAgent, DocWriterAgent,
    DevOpsAgent, PMOrchestratorAgent, CursorAgent,
    PresenterAgent, Modeler3DAgent,
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
        PresenterAgent(room),
        Modeler3DAgent(room),
    ]

    # Регистрируем всех агентов
    for agent in agents:
        room.register_agent(agent)

    from integrations.seed_knowledge import seed_all_agents
    seeded = seed_all_agents(room.agents)
    print(f"📚 Seed knowledge: {sum(seeded.values())} topics loaded")

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
    figma_studio_task = None
    git_sync_task = asyncio.create_task(auto_sync_loop(room, interval=git_interval))
    if cfg_module.config.get("figma_study_enabled", True):
        from integrations.figma_learning import sonya_figma_studio_loop
        fmin = cfg_module.config.get("figma_study_interval_min", 12)
        fmax = cfg_module.config.get("figma_study_interval_max", 25)
        figma_studio_task = asyncio.create_task(sonya_figma_studio_loop(room, fmin, fmax))
        print(f"🎨 Sonya Figma Studio: включён (каждые {fmin}-{fmax} мин)")

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

    from integrations.telegram_bot import start_bot
    await start_bot(room)

    yield  # Приложение работает

    from integrations.telegram_bot import stop_bot
    await stop_bot()

    # Остановка
    state_task.cancel()
    github_poll_task.cancel()
    git_sync_task.cancel()
    if figma_studio_task:
        figma_studio_task.cancel()
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

from middleware.auth_rate import AuthRateMiddleware
app.add_middleware(AuthRateMiddleware)

# Подключаем статику
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ─── REST API ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Главный сайт — лендинг с входом и регистрацией"""
    html_file = os.path.join(static_dir, "landing.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return RedirectResponse("/app")


@app.get("/startup", response_class=HTMLResponse)
async def startup_landing():
    """Landing page для стартапа — hero, features, CTA"""
    html_file = os.path.join(static_dir, "startup.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    raise HTTPException(status_code=404, detail="Startup landing not found")


@app.get("/app", response_class=HTMLResponse)
async def app_spa():
    """Рабочее приложение — 3D студия и Dashboard"""
    html_file = os.path.join(static_dir, "index.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h1>Static files not found</h1>")


# ─── Auth API ───────────────────────────────────────────────

class AuthRegister(BaseModel):
    email: str
    password: str
    name: str = ""


class AuthLogin(BaseModel):
    email: str
    password: str


class AuthSetup(BaseModel):
    name: str = ""
    goal: str = ""
    default_view: str = "dashboard"
    theme: str = "dark"


def _set_session_cookie(response, token: str):
    from room.user_auth import SESSION_COOKIE, SESSION_DAYS
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        max_age=SESSION_DAYS * 86400,
        samesite="lax",
        path="/",
    )


def _get_session_token(request) -> str:
    from room.user_auth import SESSION_COOKIE
    return request.cookies.get(SESSION_COOKIE, "")


@app.post("/api/auth/register")
async def auth_register(body: AuthRegister):
    from fastapi.responses import JSONResponse
    from room.user_auth import register
    try:
        user, token = register(body.email, body.password, body.name)
        resp = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(resp, token)
        return resp
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def auth_login(body: AuthLogin):
    from fastapi.responses import JSONResponse
    from room.user_auth import login
    try:
        user, token = login(body.email, body.password)
        resp = JSONResponse({"ok": True, "user": user})
        _set_session_cookie(resp, token)
        return resp
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    from fastapi.responses import JSONResponse
    from room.user_auth import logout, SESSION_COOKIE
    token = _get_session_token(request)
    logout(token)
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@app.get("/api/auth/me")
async def auth_me(request: Request):
    from room.user_auth import get_user_from_token
    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@app.post("/api/auth/setup")
async def auth_setup(body: AuthSetup, request: Request):
    from room.user_auth import get_user_from_token, complete_setup
    from room.project_memory import set_memory
    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    updated = complete_setup(
        user["id"],
        name=body.name,
        goal=body.goal,
        default_view=body.default_view,
        theme=body.theme,
    )
    if body.goal:
        set_memory(brief=body.goal, goals=[], constraints=[])
    return {"ok": True, "user": updated}


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
        "figma_configured": _figma_is_configured(),
        "figma_oauth_app": bool(cfg_module.config.get("figma_client_id") and cfg_module.config.get("figma_client_secret")),
        "figma_default_url": cfg_module.config.get("figma_default_url", ""),
        "git_auto_sync": cfg_module.config.get("git_auto_sync", True),
        "git_sync_interval_sec": cfg_module.config.get("git_sync_interval_sec", 60),
        "llm_configured": _llm_is_configured(),
        "llm_model": cfg_module.config.get("llm_model", "gpt-4o-mini"),
        "auto_theme": cfg_module.config.get("auto_theme", False),
        "telegram_notify_tasks": cfg_module.config.get("telegram_notify_tasks", False),
    }


def _llm_is_configured() -> bool:
    try:
        from integrations.llm_client import is_configured
        return is_configured()
    except Exception:
        return False


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
        "figma_configured": _figma_is_configured(),
        "git_auto_sync": cfg_module.config.get("git_auto_sync", True),
        "cursor_enabled": cfg_module.config.get("cursor_enabled", False),
        "cursor_repo_url": cfg_module.config.get("cursor_repo_url", ""),
        "git": git,
    }


@app.get("/api/activity")
async def get_activity(limit: int = 30):
    """Последние события рабочего канала для ленты активности."""
    items = []
    for msg in reversed(room.work_history[-limit * 2:]):
        msg_type = msg.get("type", "message")
        if msg_type in ("agents_state", "history", "task_history", "direct_user_echo"):
            continue
        preview = (msg.get("message") or msg.get("text") or "")[:120]
        if not preview and msg_type not in ("github_sync_started", "github_sync_done", "git_sync_done"):
            continue
        items.append({
            "type": msg_type,
            "message": preview,
            "agent_id": msg.get("agent_id"),
            "agent_name": msg.get("agent_name"),
            "agent_emoji": msg.get("agent_emoji"),
            "timestamp": msg.get("timestamp"),
        })
        if len(items) >= limit:
            break
    return {"items": items, "count": len(items)}


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


@app.get("/api/pipeline")
async def get_pipeline():
    return {"pipeline": room.pipeline.get_state()}


# ─── Figma ────────────────────────────────────────────────────

def _figma_is_configured() -> bool:
    from integrations.figma_oauth import is_figma_connected
    return is_figma_connected()


@app.get("/api/figma/status")
async def figma_status():
    from integrations.figma_oauth import get_connection_status
    return await get_connection_status()


@app.get("/api/figma/auth")
async def figma_auth_start():
    from integrations.figma_oauth import oauth_app_configured, build_auth_url, get_redirect_uri

    if not oauth_app_configured():
        raise HTTPException(
            status_code=400,
            detail="FIGMA_CLIENT_ID и FIGMA_CLIENT_SECRET не заданы в .env",
        )
    return {"auth_url": build_auth_url(), "redirect_uri": get_redirect_uri()}


@app.get("/api/figma/callback")
async def figma_oauth_callback(code: str = "", state: str = "", error: str = ""):
    from integrations.figma_oauth import verify_state, complete_oauth

    if error:
        return RedirectResponse("/?figma=denied")
    if not code or not state or not verify_state(state):
        return RedirectResponse("/?figma=error")
    try:
        await complete_oauth(code)
        return RedirectResponse("/?figma=connected")
    except Exception:
        return RedirectResponse("/?figma=error")


@app.post("/api/figma/disconnect")
async def figma_disconnect():
    from integrations.figma_oauth import clear_token_store
    clear_token_store()
    return {"ok": True}


@app.get("/api/figma/studio")
async def figma_studio_stats():
    from integrations.figma_learning import get_studio_stats, load_portfolio
    stats = get_studio_stats()
    frontend = room.agents.get("frontend")
    if frontend:
        state = frontend.get_state()
        stats["agent"] = {
            "figma_studies": state.get("figma_studies", 0),
            "figma_creations": state.get("figma_creations", 0),
            "status": frontend.status,
        }
    stats["portfolio"] = load_portfolio()[:20]
    return stats


@app.post("/api/figma/studio/trigger")
async def figma_studio_trigger(action: str = "study"):
    """Ручной запуск обучения/создания Сони в Figma."""
    from integrations.figma_learning import run_figma_study_session, run_figma_create_session
    from integrations.figma_oauth import is_figma_connected

    if not is_figma_connected():
        raise HTTPException(status_code=400, detail="Figma не подключена")

    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")

    if action == "create":
        ok = await run_figma_create_session(frontend)
    else:
        ok = await run_figma_study_session(frontend)
    await room.send_agents_state()
    return {"ok": ok, "action": action}


@app.post("/api/figma/import")
async def figma_import(request: FigmaImportRequest):
    """Импорт макета из Figma по URL."""
    from integrations.figma_client import get_client_async, parse_figma_url

    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL обязателен")
    parsed = parse_figma_url(request.url)
    if not parsed:
        raise HTTPException(status_code=400, detail="Некорректная ссылка Figma")

    from integrations.figma_fixtures import get_fixture

    client = await get_client_async()
    has_fixture = bool(get_fixture(parsed["file_key"]))
    if not client.configured and not has_fixture:
        raise HTTPException(
            status_code=400,
            detail="Figma не подключена. Нажмите «Подключить Figma» или добавьте FIGMA_ACCESS_TOKEN в .env",
        )
    try:
        result = await client.import_design(request.url)
    except Exception as e:
        from integrations.figma_rate_limit import FigmaRateLimitError
        if isinstance(e, FigmaRateLimitError):
            raise HTTPException(
                status_code=429,
                detail=str(e),
                headers={"Retry-After": str(int(e.retry_after))},
            )
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


class FigmaCompareRequest(BaseModel):
    figma_colors: list = []
    react_colors: list = []


@app.post("/api/figma/compare")
async def figma_compare(req: FigmaCompareRequest):
    from integrations.figma_compare import compare_palettes
    return compare_palettes(req.figma_colors, req.react_colors)


@app.post("/api/figma/improve")
async def figma_improve():
    """Соня дорабатывает UI по последнему Figma-макету."""
    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")
    task = "Доработай React UI точнее по импортированному Figma-макету: цвета, spacing, типографика"
    await room.handle_user_message({"type": "task", "text": task, "target": "frontend"})
    return {"ok": True, "task": task}


@app.get("/api/standup")
async def get_standup():
    from integrations.standup import generate_standup
    return generate_standup(room)


@app.get("/api/timeline")
async def get_timeline(limit: int = 100):
    from integrations.timeline_store import get_events
    return {"events": get_events(limit=min(limit, 500))}


@app.get("/api/timeline/replay")
async def get_timeline_replay(hours: float = 1.0):
    from integrations.timeline_store import replay_summary
    return replay_summary(hours=min(max(hours, 0.25), 24))


@app.get("/api/kanban")
async def get_kanban():
    columns = {"submitted": [], "in_progress": [], "completed": [], "failed": []}
    for task in room.task_history.get_all():
        status = task.get("status", "submitted")
        key = status if status in columns else "submitted"
        if status == "queued":
            key = "submitted"
        columns[key].append(task)
    return {"columns": columns}


@app.get("/api/projects")
async def list_projects(agent_id: str = "", type: str = "", limit: int = 80):
    from room.artifact_store import list_all, stats
    items = list_all(limit=min(limit, 200), agent_id=agent_id or None, art_type=type or None)
    full = []
    for meta in items:
        from room.artifact_store import get_artifact
        art = get_artifact(meta["id"])
        if art:
            preview = art.get("preview_html") or art.get("content", "")
            full.append({**meta, "has_preview": bool(preview), "file_count": len(art.get("files") or {})})
    return {"projects": full, "stats": stats()}


@app.get("/api/projects/{artifact_id}")
async def get_project(artifact_id: str):
    from room.artifact_store import get_artifact
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Project not found")
    return art


@app.get("/api/projects/{artifact_id}/preview", response_class=HTMLResponse)
async def project_preview(artifact_id: str):
    from room.artifact_store import get_artifact
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Not found")
    html = art.get("preview_html") or ""
    if not html and art.get("type") in ("presentation", "model_3d"):
        html = art.get("content", "")
    if not html:
        content = art.get("content", art.get("description", ""))
        html = f"<!DOCTYPE html><html><body><pre style='font-family:monospace;padding:24px'>{content}</pre></body></html>"
    return HTMLResponse(html)


@app.get("/api/agents/{agent_id}/activity")
async def agent_activity(agent_id: str):
    from room.artifact_store import get_agent_artifacts, stats as art_stats
    from room.agent_capabilities import get_capabilities
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    artifacts = get_agent_artifacts(agent_id, limit=40)
    detailed = []
    for meta in artifacts[:15]:
        from room.artifact_store import get_artifact
        a = get_artifact(meta["id"])
        if a:
            detailed.append(a)
    tasks = [t for t in room.task_history.get_all() if t.get("agent_id") == agent_id][:20]
    return {
        "agent": agent.get_state(),
        "capabilities": get_capabilities(agent_id),
        "artifacts": detailed,
        "artifact_stats": art_stats().get("by_agent", {}).get(agent_id, 0),
        "recent_tasks": tasks,
        "direct_chat_count": len(agent.direct_chat),
    }


class ReviseRequest(BaseModel):
    artifact_id: str = ""
    instruction: str


@app.post("/api/agents/{agent_id}/revise")
async def revise_artifact(agent_id: str, body: ReviseRequest):
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not body.instruction.strip():
        raise HTTPException(status_code=400, detail="instruction required")
    from room.artifact_store import get_artifact
    art = get_artifact(body.artifact_id) if body.artifact_id else None
    title = art.get("title", "проект") if art else "проект"
    task = f"Доработка «{title}»: {body.instruction.strip()}"
    child_id = room.task_history.add_queued(task, agent_id, agent.name, agent.emoji, sender="Ревизия")
    await agent.assign_task(task, sender="Ревизия", task_id=child_id)
    return {"ok": True, "task": task, "artifact_id": body.artifact_id}


@app.get("/api/templates")
async def get_templates():
    from integrations.project_templates import list_templates
    return {"templates": list_templates()}


class TemplateApplyRequest(BaseModel):
    template_id: str


@app.post("/api/templates/apply")
async def apply_project_template(body: TemplateApplyRequest):
    from integrations.project_templates import get_template
    tpl = get_template(body.template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await room.handle_user_message({"type": "task", "text": tpl["task"], "target": "all"})
    return {"ok": True, "template": tpl["id"], "task": tpl["task"]}


@app.get("/api/integrations/status")
async def integrations_status():
    from integrations.external_hub import integration_status
    from integrations.llm_client import is_configured
    from integrations.telegram_bot import bot_status
    status = integration_status()
    status["llm"] = is_configured()
    tg = bot_status()
    status["telegram_bot"] = tg.get("username")
    status["telegram_polling"] = tg.get("polling")
    return status


class IntegrationTextRequest(BaseModel):
    text: str = ""
    title: str = "AI Team Export"
    content: str = ""


@app.post("/api/integrations/telegram")
async def send_telegram_msg(body: IntegrationTextRequest):
    from integrations.external_hub import send_telegram
    result = await send_telegram(body.text or body.content)
    if not result:
        return {"ok": False, "message": "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set"}
    return {"ok": True, "result": result}


@app.post("/api/integrations/notion/export")
async def export_to_notion(body: IntegrationTextRequest):
    from integrations.external_hub import export_notion_page
    result = await export_notion_page(body.title, body.content or body.text)
    if not result:
        return {"ok": False, "message": "NOTION_TOKEN / NOTION_PARENT_PAGE_ID not set"}
    return {"ok": True, "result": result}


@app.post("/api/integrations/vercel/deploy")
async def vercel_deploy_endpoint():
    from integrations.external_hub import deploy_vercel
    result = await deploy_vercel()
    if not result:
        return {"ok": False, "message": "VERCEL_TOKEN not set"}
    return result


@app.post("/api/telegram/webhook")
async def telegram_webhook(payload: dict):
    """Telegram Bot webhook → управление командой."""
    from integrations.telegram_bot import handle_update
    await handle_update(payload, room)
    return {"ok": True}


@app.get("/api/telegram/status")
async def telegram_status():
    from integrations.telegram_bot import bot_status
    return bot_status()


@app.post("/api/telegram/restart")
async def telegram_restart():
    from integrations.telegram_bot import stop_bot, start_bot, bot_status
    await stop_bot()
    await start_bot(room)
    return {"ok": True, **bot_status()}


# ─── Power Pack API ─────────────────────────────────────────

class ProjectMemoryUpdate(BaseModel):
    brief: str = ""
    goals: list = []
    constraints: list = []


@app.get("/api/project-memory")
async def get_project_memory():
    from room.project_memory import get_memory
    return get_memory()


@app.post("/api/project-memory")
async def set_project_memory(body: ProjectMemoryUpdate):
    from room.project_memory import set_memory
    return set_memory(brief=body.brief, goals=body.goals, constraints=body.constraints)


@app.get("/api/sprint")
async def get_sprint_api():
    from room.sprint_store import get_sprint
    return get_sprint()


class SprintStart(BaseModel):
    name: str
    goal: str
    days: int = 7


@app.post("/api/sprint/start")
async def start_sprint_api(body: SprintStart):
    from room.sprint_store import start_sprint
    return start_sprint(body.name, body.goal, body.days)


class SprintBacklogItem(BaseModel):
    text: str
    priority: str = "medium"


@app.post("/api/sprint/backlog")
async def add_sprint_backlog(body: SprintBacklogItem):
    from room.sprint_store import add_backlog_item
    return add_backlog_item(body.text, body.priority)


@app.post("/api/sprint/backlog/{item_id}/toggle")
async def toggle_sprint_item(item_id: str):
    from room.sprint_store import toggle_backlog
    return toggle_backlog(item_id)


@app.post("/api/sprint/end")
async def end_sprint_api():
    from room.sprint_store import end_sprint
    return end_sprint()


@app.get("/api/projects/{artifact_id}/diff/{other_id}")
async def artifact_diff(artifact_id: str, other_id: str):
    from room.artifact_store import get_artifact
    from room.artifact_diff import diff_artifacts
    a = get_artifact(artifact_id)
    b = get_artifact(other_id)
    if not a or not b:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return diff_artifacts(a, b)


@app.post("/api/projects/{artifact_id}/create-pr")
async def artifact_create_pr(artifact_id: str):
    from room.artifact_store import get_artifact
    from integrations.pr_from_artifact import create_pr_from_artifact
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Not found")
    art["agent_id"] = art.get("agent_id")
    return await create_pr_from_artifact(art, room_manager=room)


@app.get("/api/projects/{artifact_id}/export")
async def artifact_export(artifact_id: str, format: str = "html"):
    from room.artifact_store import get_artifact
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Not found")
    html = art.get("preview_html") or art.get("content") or ""
    if format == "print":
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{art.get('title')}</title>
<style>@media print{{body{{margin:0}}}}</style></head><body>{html}
<script>window.onload=()=>window.print()</script></body></html>"""
    return HTMLResponse(html)


@app.get("/api/llm/usage")
async def llm_usage_stats():
    from integrations.llm_usage import get_stats
    return get_stats()


@app.get("/api/artifact-templates")
async def artifact_templates_list():
    from integrations.artifact_templates import list_templates
    return {"templates": list_templates()}


@app.post("/api/artifact-templates/{template_id}/apply")
async def apply_artifact_template(template_id: str):
    from integrations.artifact_templates import list_templates
    tpl = next((t for t in list_templates() if t["id"] == template_id), None)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await room.handle_user_message({"type": "task", "text": tpl["task"], "target": tpl["target"]})
    return {"ok": True, "template": tpl}


@app.post("/api/pipeline/full")
async def pipeline_full(figma_url: str = ""):
    from integrations.pipeline_oneclick import run_full_pipeline
    return await run_full_pipeline(room, figma_url or None)


@app.post("/api/webhook/task")
async def webhook_task(payload: dict):
    text = payload.get("text") or payload.get("message") or payload.get("task") or ""
    target = payload.get("target", "all")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text required")
    await room.handle_user_message({"type": "task", "text": text, "target": target})
    return {"ok": True}


@app.get("/api/backup/download")
async def backup_download():
    from integrations.backup_restore import create_backup
    from fastapi.responses import Response
    data = create_backup()
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=ai-team-backup.zip"},
    )


@app.post("/api/view-token")
async def create_view_token(hours: int = 72, label: str = "client"):
    from room.view_tokens import create_token
    t = create_token(hours=hours, label=label)
    return {"ok": True, "url": f"/?view={t['token']}", **t}


class TaskPriorityUpdate(BaseModel):
    priority: str


@app.patch("/api/tasks/{task_id}/priority")
async def update_task_priority(task_id: str, body: TaskPriorityUpdate):
    ok = room.task_history.set_priority(task_id, body.priority)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    await room._broadcast_task_history()
    return {"ok": True}


@app.get("/api/mentions/aliases")
async def mention_aliases():
    from room.mention_parser import list_aliases
    return {"aliases": list_aliases()}


@app.post("/api/deploy")
async def deploy_preview():
    from integrations.deploy_export import create_deploy_bundle
    info = create_deploy_bundle()
    await room.broadcast_work({
        "type": "deploy_ready",
        "message": f"🚀 Deploy bundle готов: {info['download_url']}",
        "download_url": info["download_url"],
        "preview_url": info["preview_url"],
        "timestamp": __import__("datetime").datetime.now().isoformat(),
    })
    return info


@app.get("/api/deploy/download")
async def deploy_download():
    path = os.path.join(os.path.dirname(__file__), "output", "deploy", "latest.zip")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Сначала нажмите Deploy")
    return FileResponse(path, filename="ai-team-preview.zip", media_type="application/zip")


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
