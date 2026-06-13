import asyncio
import json
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, Response
from pydantic import BaseModel

from room.room_manager import RoomManager
from agents import (
    ArchitectAgent, BackendDevAgent, FrontendDevAgent,
    QATesterAgent, CodeReviewerAgent, DocWriterAgent,
    DevOpsAgent, PMOrchestratorAgent, CursorAgent,
    PresenterAgent, Modeler3DAgent, EvaluatorAgent, SecurityAgent,
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
        EvaluatorAgent(room),
        SecurityAgent(room),
    ]

    # Регистрируем всех агентов
    for agent in agents:
        room.register_agent(agent)

    from integrations.seed_knowledge import seed_all_agents
    seeded = seed_all_agents(room.agents)
    print(f"📚 Seed knowledge: {sum(seeded.values())} topics loaded")

    try:
        from integrations.figma_theme import ensure_theme_files
        theme = ensure_theme_files()
        print(f"🎨 Snow theme: {theme.get('source', 'ok')} (accent {theme.get('light', {}).get('accent', '')})")
    except Exception as e:
        print(f"⚠️ Snow theme init: {e}")

    try:
        from integrations.rag.ingest import ensure_indexed
        rag = ensure_indexed(min_total=400)
        if rag.get("skipped"):
            print(f"📚 RAG knowledge: {rag.get('total')} chunks (cached)")
        else:
            print(f"📚 RAG knowledge indexed: {rag.get('total', 0)} chunks")
    except Exception as e:
        print(f"⚠️ RAG init: {e}")

    async def _embed_background():
        try:
            from integrations.rag.embed_index import ensure_embeddings
            emb = await ensure_embeddings()
            if emb.get("embedded"):
                print(f"🧠 RAG embeddings: {emb.get('vectors', 0)} vectors")
            elif emb.get("skipped"):
                print(f"🧠 RAG embeddings: {emb.get('vectors', 0)} (cached)")
        except Exception as e:
            print(f"⚠️ RAG embeddings: {e}")

    asyncio.create_task(_embed_background())

    room.task_history.cleanup_stale(max_minutes=30)
    cancelled = room.task_history.stats().get("cancelled", 0)
    if cancelled:
        print(f"🧹 Зависших/старых задач отменено: {cancelled}")

    owner_email = os.environ.get("OWNER_EMAIL", "").strip()
    owner_password = os.environ.get("OWNER_PASSWORD", "").strip()
    if owner_email and owner_password:
        from room.user_auth import ensure_owner
        owner = ensure_owner(
            owner_email,
            owner_password,
            os.environ.get("OWNER_NAME", "Owner"),
        )
        print(f"👑 Owner account ready: {owner['email']}")

    from room.user_auth import bootstrap_primary_owner
    primary = bootstrap_primary_owner("takura.anigatsuki@gmail.com")
    if primary:
        print(f"👑 Primary owner upgraded: {primary['email']} (tier Owner, full access)")
        migrated = room.task_history.assign_all_orphans_to(
            primary["id"], primary.get("name") or primary.get("email", "")
        )
        if migrated:
            print(f"📋 Legacy tasks without user_id migrated: {migrated} → {primary['email']}")

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
        from integrations.figma_learning import sonya_figma_studio_loop, ensure_seed_patterns
        ensure_seed_patterns()
        fmin = cfg_module.config.get("figma_study_interval_min", 12)
        fmax = cfg_module.config.get("figma_study_interval_max", 25)
        figma_studio_task = asyncio.create_task(sonya_figma_studio_loop(room, fmin, fmax))
        print(f"🎨 Sonya Figma Studio: включён (каждые {fmin}-{fmax} мин)")
        asyncio.create_task(_bootstrap_figma_discovery(room))

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

    from room.security_monitor import get_monitor
    security_task = asyncio.create_task(_security_monitor_loop(room))

    yield  # Приложение работает

    from integrations.telegram_bot import stop_bot
    await stop_bot()

    # Остановка
    state_task.cancel()
    github_poll_task.cancel()
    git_sync_task.cancel()
    security_task.cancel()
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

from middleware.security import SecurityMiddleware
app.add_middleware(SecurityMiddleware)

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


@app.get("/cabinet")
async def cabinet_page():
    """Личный кабинет — редирект в приложение."""
    return RedirectResponse("/app?view=profile")


@app.get("/investor", response_class=HTMLResponse)
async def investor_portal_page():
    """Investor Portal — read-only метрики и pitch."""
    html_file = os.path.join(static_dir, "investor.html")
    if os.path.exists(html_file):
        with open(html_file, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return RedirectResponse("/app?view=investor")


async def _security_monitor_loop(room_mgr: RoomManager):
    """Фоновая обработка событий безопасности агентом Олег."""
    from room.security_monitor import get_monitor
    from room.feature_flags import is_enabled
    while True:
        try:
            await asyncio.sleep(5)
            if not is_enabled("security_agent"):
                continue
            agent = room_mgr.agents.get("security")
            if not agent:
                continue
            for event in get_monitor().pop_pending(3):
                await agent.handle_security_event(event)
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(10)


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


class AuthProfileUpdate(BaseModel):
    name: str | None = None
    default_view: str | None = None
    theme: str | None = None
    project_goal: str | None = None


class AuthPasswordChange(BaseModel):
    current_password: str
    new_password: str


class SubscriptionUpgradeRequest(BaseModel):
    tier: str


class AdminBalanceRequest(BaseModel):
    user_id: str
    amount: int


class AdminTierRequest(BaseModel):
    user_id: str
    tier: str


class AdminUserUpdateRequest(BaseModel):
    role: str | None = None
    name: str | None = None
    tier: str | None = None
    balance_delta: int | None = None
    set_balance: int | None = None


class AdminConsoleRequest(BaseModel):
    action: str
    text: str = ""
    target: str = "all"
    agent_id: str = ""
    repo_url: str = ""


class AdminSiteUpdate(BaseModel):
    learning_interval_min: int | None = None
    learning_interval_max: int | None = None
    persist_knowledge: bool | None = None
    cursor_enabled: bool | None = None
    cursor_model: str | None = None
    cursor_repo_url: str | None = None
    git_auto_sync: bool | None = None
    auto_theme: bool | None = None
    telegram_notify_tasks: bool | None = None


def _current_user(request: Request):
    from room.user_auth import get_user_from_token
    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    return user


def _optional_user(request: Request):
    from room.user_auth import get_user_from_token
    token = _get_session_token(request)
    return get_user_from_token(token) if token else None


def _require_feature(user: dict, feature: str):
    from room.subscriptions import can_use_feature, access_denied_message
    if not can_use_feature(user, feature):
        raise HTTPException(status_code=403, detail=access_denied_message(feature, user))


def _charge_or_forbid(user: dict, action: str):
    from room.user_auth import charge_user_action
    ok, msg = charge_user_action(user["id"], action)
    if not ok:
        raise HTTPException(status_code=402, detail=msg)


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


@app.patch("/api/auth/profile")
async def auth_update_profile(body: AuthProfileUpdate, request: Request):
    from room.user_auth import get_user_from_token, update_profile

    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    try:
        updated = update_profile(
            user["id"],
            name=body.name,
            default_view=body.default_view,
            theme=body.theme,
            project_goal=body.project_goal,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "user": updated}


@app.post("/api/auth/change-password")
async def auth_change_password(body: AuthPasswordChange, request: Request):
    from room.user_auth import get_user_from_token, change_password

    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")
    try:
        change_password(user["id"], body.current_password, body.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}


@app.get("/api/auth/profile/stats")
async def auth_profile_stats(request: Request):
    from datetime import datetime, timedelta
    from room.user_auth import get_user_from_token, _load, SESSIONS_FILE
    from integrations.sonya_studio import list_projects
    from room.project_memory import get_memory
    from room.artifact_store import stats as artifact_stats, list_all as list_artifacts
    from integrations.llm_usage import get_stats as llm_stats
    from integrations.figma_learning import get_studio_stats

    user = get_user_from_token(_get_session_token(request))
    if not user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    th = room.task_history.stats()
    mem = get_memory() or {}
    projects = list_projects()
    all_tasks = room.task_history.get_all()
    week_ago = datetime.now() - timedelta(days=7)
    tasks_week = 0
    agent_usage = {}
    for t in room.task_history.tasks:
        created = t.get("created_at")
        if created:
            try:
                if datetime.fromisoformat(created) >= week_ago:
                    tasks_week += 1
            except ValueError:
                pass
        aid = t.get("agent_id") or t.get("target")
        if aid:
            agent_usage[aid] = agent_usage.get(aid, 0) + 1

    total = th.get("total") or 0
    completed = th.get("completed") or 0
    success_rate = round(completed / total * 100) if total else 0

    sessions_raw = _load(SESSIONS_FILE)
    active_sessions = 0
    if isinstance(sessions_raw, dict):
        active_sessions = sum(
            1 for s in sessions_raw.values() if s.get("user_id") == user.get("id")
        )

    member_since = user.get("created_at")
    days_member = 0
    if member_since:
        try:
            days_member = max(0, (datetime.now() - datetime.fromisoformat(member_since)).days)
        except ValueError:
            pass

    sub = user.get("subscription") or {}
    llm = llm_stats()
    arts = artifact_stats()
    figma = get_studio_stats()
    top_agents = sorted(agent_usage.items(), key=lambda x: -x[1])[:5]

    def _task_row(t):
        return {
            "id": t.get("id"),
            "task": (t.get("task") or "")[:140],
            "status": t.get("status"),
            "agent_name": t.get("agent_name"),
            "agent_emoji": t.get("agent_emoji"),
            "sender": t.get("sender"),
            "created_at": t.get("created_at"),
            "completed_at": t.get("completed_at"),
        }

    return {
        "tasks_total": total,
        "tasks_completed": completed,
        "tasks_active": th.get("active", 0),
        "tasks_failed": th.get("failed", 0),
        "tasks_week": tasks_week,
        "success_rate": success_rate,
        "sonya_projects": len(projects),
        "sonya_published": sum(1 for p in projects if p.get("status") == "published"),
        "sonya_draft": sum(1 for p in projects if p.get("status") != "published"),
        "artifacts_total": arts.get("total", 0),
        "artifacts_by_type": arts.get("by_type", {}),
        "llm_requests": llm.get("total_requests", 0),
        "llm_tokens_in": llm.get("total_input_tokens", 0),
        "llm_tokens_out": llm.get("total_output_tokens", 0),
        "llm_cost_usd": llm.get("estimated_cost_usd", 0),
        "llm_cost_rub": llm.get("estimated_cost_rub", 0),
        "figma_patterns": figma.get("studied_count", 0),
        "figma_portfolio": figma.get("portfolio_count", 0),
        "agents_online": len(room.agents),
        "agents_busy": sum(
            1 for a in room.agents.values()
            if a.get_state().get("status") in ("working", "learning")
        ),
        "agents_total": len(room.agents),
        "top_agents": [{"id": k, "count": v} for k, v in top_agents],
        "has_project_brief": bool(mem.get("brief") or user.get("project_goal")),
        "project_goals_count": len(mem.get("goals") or []),
        "project_constraints_count": len(mem.get("constraints") or []),
        "memory_updated_at": mem.get("updated_at"),
        "member_since": member_since,
        "days_member": days_member,
        "setup_at": user.get("setup_at"),
        "updated_at": user.get("updated_at"),
        "active_sessions": active_sessions,
        "views_unlocked_count": len(sub.get("views_unlocked") or []),
        "subscription": sub,
        "access_level": user.get("access_level"),
        "recent_tasks": [_task_row(t) for t in all_tasks[:12]],
        "recent_projects": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "status": p.get("status"),
                "updated_at": p.get("updated_at"),
            }
            for p in projects[:6]
        ],
        "recent_artifacts": list_artifacts(limit=6),
    }


@app.get("/api/subscription/plans")
async def subscription_plans():
    from room.subscriptions import list_plans_public, ACTION_COSTS
    return {"plans": list_plans_public(), "action_costs": ACTION_COSTS}


@app.get("/api/subscription/me")
async def subscription_me(request: Request):
    user = _current_user(request)
    return {"subscription": user.get("subscription"), "role": user.get("role"), "access_level": user.get("access_level")}


@app.get("/api/subscription/access")
async def subscription_access(request: Request, view: str = "", feature: str = ""):
    from room.subscriptions import can_access_view, can_use_feature, access_denied_message, get_action_cost
    from room.user_auth import get_user_from_token

    user = get_user_from_token(_get_session_token(request))
    allowed = True
    reason = ""
    if view:
        allowed = can_access_view(user, view)
        if not allowed:
            reason = access_denied_message(view, user)
    elif feature:
        allowed = can_use_feature(user, feature)
        if not allowed:
            reason = access_denied_message(feature, user)
    return {
        "allowed": allowed,
        "reason": reason,
        "cost": get_action_cost(feature) if feature else 0,
        "subscription": (user or {}).get("subscription"),
    }


@app.post("/api/subscription/upgrade")
async def subscription_upgrade(body: SubscriptionUpgradeRequest, request: Request):
    """Демо-апгрейд тарифа (без оплаты — для тестирования). Owner может любой tier кроме owner."""
    from room.subscriptions import set_subscription_tier, SUBSCRIPTION_PLANS
    from room.user_auth import _load, _save_users, USERS_FILE, get_user_from_token

    user = _current_user(request)
    tier = body.tier.lower().strip()
    if tier not in SUBSCRIPTION_PLANS or tier == "owner":
        raise HTTPException(status_code=400, detail="Недоступный тариф")
    if user.get("role") == "owner":
        return {"ok": True, "message": "У владельца уже максимальный уровень Owner", "user": user}
    cur_level = user.get("access_level", 1)
    new_level = SUBSCRIPTION_PLANS[tier]["level"]
    if new_level <= cur_level:
        raise HTTPException(status_code=400, detail="Выберите тариф выше текущего")
    set_subscription_tier(
        user["id"],
        tier,
        users_loader=lambda: _load(USERS_FILE),
        users_saver=_save_users,
    )
    updated = get_user_from_token(_get_session_token(request))
    return {"ok": True, "user": updated, "message": f"Тариф обновлён до {SUBSCRIPTION_PLANS[tier]['name_ru']}"}


class StripeCheckoutBody(BaseModel):
    tier: str
    success_url: str = ""
    cancel_url: str = ""


@app.get("/api/billing/stripe/status")
async def stripe_billing_status():
    from integrations.stripe_billing import status as stripe_status
    from room.feature_flags import is_enabled
    s = stripe_status()
    s["enabled"] = is_enabled("stripe_billing") and s["configured"]
    return s


@app.post("/api/billing/stripe/checkout")
async def stripe_checkout(body: StripeCheckoutBody, request: Request):
    from integrations.stripe_billing import create_checkout_session, is_configured
    from room.feature_flags import is_enabled
    if not is_enabled("stripe_billing") or not is_configured():
        raise HTTPException(status_code=503, detail="Stripe billing не настроен")
    user = _current_user(request)
    base = str(request.base_url).rstrip("/")
    success = body.success_url or f"{base}/app?view=profile"
    cancel = body.cancel_url or f"{base}/app?view=profile"
    try:
        session = await create_checkout_session(
            user_id=user["id"],
            user_email=user["email"],
            tier=body.tier.lower().strip(),
            success_url=success,
            cancel_url=cancel,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "url": session.get("url"), "session_id": session.get("id")}


@app.post("/api/billing/stripe/webhook")
async def stripe_webhook(request: Request):
    from integrations.stripe_billing import verify_webhook, handle_webhook_event
    from room.user_auth import _load, _save_users, USERS_FILE
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    if not verify_webhook(payload, sig):
        raise HTTPException(status_code=400, detail="Invalid signature")
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    result = handle_webhook_event(
        event,
        users_loader=lambda: _load(USERS_FILE),
        users_saver=_save_users,
    )
    from room import notifications
    if result.get("action") == "subscription_activated":
        notifications.push(
            "Подписка активирована",
            f"Тариф {result.get('tier')} успешно подключён",
            user_id=result.get("user_id", ""),
            ntype="billing",
        )
    return result


@app.post("/api/admin/billing/topup")
async def admin_billing_topup(body: AdminBalanceRequest, request: Request):
    from room.user_auth import admin_add_balance

    admin = _current_user(request)
    if not admin.get("is_owner") and "manage_users" not in (admin.get("privileges") or []):
        raise HTTPException(status_code=403, detail="Только владелец или админ")
    try:
        target = admin_add_balance(admin, body.user_id, body.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "user": target}


@app.post("/api/admin/billing/set-tier")
async def admin_billing_set_tier(body: AdminTierRequest, request: Request):
    from room.user_auth import admin_set_user_tier

    admin = _current_user(request)
    if not admin.get("is_owner"):
        raise HTTPException(status_code=403, detail="Только владелец")
    try:
        target = admin_set_user_tier(admin, body.user_id, body.tier)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "user": target}


@app.get("/api/admin/users")
async def admin_list_users_route(request: Request):
    from room.user_auth import admin_list_users, can_manage_users

    admin = _current_user(request)
    if not can_manage_users(admin):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    try:
        users = admin_list_users(admin)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    return {"users": users, "total": len(users)}


@app.patch("/api/admin/users/{user_id}")
async def admin_update_user_route(user_id: str, body: AdminUserUpdateRequest, request: Request):
    from room.user_auth import admin_update_user, can_manage_users

    admin = _current_user(request)
    if not can_manage_users(admin):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    try:
        updated = admin_update_user(
            admin,
            user_id,
            role=body.role,
            name=body.name,
            tier=body.tier,
            balance_delta=body.balance_delta,
            set_balance=body.set_balance,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "user": updated}


@app.get("/api/admin/site")
async def admin_get_site(request: Request):
    from room.user_auth import can_manage_site

    admin = _current_user(request)
    if not can_manage_site(admin):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    cfg = await get_config()
    agents = await get_agents()
    return {
        "config": cfg,
        "agents_count": len(agents.get("agents", [])),
        "active_agents": sum(1 for a in agents.get("agents", []) if a.get("status") in ("working", "thinking", "learning")),
    }


@app.patch("/api/admin/site")
async def admin_update_site(body: AdminSiteUpdate, request: Request):
    from room.user_auth import can_manage_site

    admin = _current_user(request)
    if not can_manage_site(admin):
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    update = ConfigUpdate(
        learning_interval_min=body.learning_interval_min,
        learning_interval_max=body.learning_interval_max,
        persist_knowledge=body.persist_knowledge,
        cursor_repo_url=body.cursor_repo_url,
        cursor_enabled=body.cursor_enabled,
        git_auto_sync=body.git_auto_sync,
    )
    result = await update_config(update)
    import config as cfg_module
    if body.cursor_model:
        cfg_module.config["cursor_model"] = body.cursor_model.strip()
        config_file = os.path.join(os.path.dirname(__file__), "config.json")
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = {}
        current["cursor_model"] = body.cursor_model.strip()
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
    if body.auto_theme is not None:
        cfg_module.config["auto_theme"] = body.auto_theme
    if body.telegram_notify_tasks is not None:
        cfg_module.config["telegram_notify_tasks"] = body.telegram_notify_tasks
    return {"ok": True, "config": result}


@app.post("/api/admin/console")
async def admin_console(body: AdminConsoleRequest, request: Request):
    from room.user_auth import can_access_admin

    admin = _current_user(request)
    if not can_access_admin(admin):
        raise HTTPException(status_code=403, detail="Консоль доступна только администраторам")

    action = (body.action or "").strip().lower()
    text = (body.text or "").strip()
    log = [f"[{action}] {text[:120]}" if text else f"[{action}]"]

    if action == "team_task":
        if not text:
            raise HTTPException(status_code=400, detail="Укажите текст задачи")
        await room.handle_user_message({"type": "task", "text": text, "target": body.target or "all"})
        log.append("Задача отправлена команде через PM")
        return {"ok": True, "log": log, "message": "Задача поставлена"}

    if action == "agent_task":
        if not text or not body.agent_id:
            raise HTTPException(status_code=400, detail="Нужны agent_id и text")
        agent = room.agents.get(body.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Агент не найден")
        await agent.assign_task(text, sender=admin.get("name") or "Admin")
        log.append(f"Задача → {body.agent_id}")
        return {"ok": True, "log": log, "message": f"Задача агенту {body.agent_id}"}

    if action == "cursor_run":
        if not text:
            raise HTTPException(status_code=400, detail="Укажите prompt для Cursor")
        run_req = CursorRunRequest(prompt=text, repo_url=body.repo_url or "")
        result = await cursor_run(run_req)
        log.append(f"Cursor run: {result.get('run_id', '—')}")
        return {"ok": True, "log": log, "result": result}

    if action == "git_sync":
        result = await git_sync_now()
        log.append(f"Git: {result.get('action', '—')}")
        return {"ok": True, "log": log, "result": result}

    if action == "pipeline":
        from integrations.pipeline_oneclick import run_full_pipeline
        result = await run_full_pipeline(room)
        log.append("Pipeline запущен")
        return {"ok": True, "log": log, "result": result}

    if action == "broadcast":
        if not text:
            raise HTTPException(status_code=400, detail="Укажите текст")
        await room.broadcast_work({
            "type": "system",
            "message": text,
            "from": admin.get("name") or "Admin",
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        log.append("Сообщение в комнату")
        return {"ok": True, "log": log}

    raise HTTPException(status_code=400, detail=f"Неизвестное действие: {action}")


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
async def assign_task(http_request: Request, body: TaskRequest):
    """Назначить задачу через REST API"""
    user = _optional_user(http_request)
    if user:
        from room.task_limits import check_and_record
        ok, msg = check_and_record(user)
        if not ok:
            raise HTTPException(status_code=429, detail=msg)
        _charge_or_forbid(user, "task")
    await room.handle_user_message({
        "type": "task",
        "text": body.text,
        "target": body.target
    }, user=user)
    return {"status": "ok", "message": f"Задача назначена: {body.text}"}


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
async def send_direct_chat(agent_id: str, http_request: Request, request: DirectChatRequest):
    """Отправить личное сообщение агенту"""
    user = _optional_user(http_request)
    agent = room.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Агент не найден")
    uid = user.get("id", "") if user else ""
    uname = (user.get("name") or user.get("email", "User").split("@")[0]) if user else ""
    await agent.handle_direct_chat(request.text, user_id=uid, user_name=uname)
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
    github_sync_on_tasks: bool = None
    m365_enabled: bool = None


class CursorRunRequest(BaseModel):
    prompt: str
    repo_url: str = ""


class FigmaImportRequest(BaseModel):
    url: str


class FigmaStudyUrlRequest(BaseModel):
    url: str = ""


class SonyaProjectCreate(BaseModel):
    title: str = ""
    task: str = ""
    description: str = ""


class SonyaCommentCreate(BaseModel):
    text: str
    x: float = 0.5
    y: float = 0.5
    frame_id: str = "main"


class SonyaPublishRequest(BaseModel):
    figma_url: str = ""


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
        "github_sync_on_tasks": cfg_module.config.get("github_sync_on_tasks", False),
        "m365_enabled": cfg_module.config.get("m365_enabled", True),
        "m365_configured": _m365_is_configured(),
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


def _m365_is_configured() -> bool:
    try:
        from integrations.m365_client import is_configured
        return is_configured()
    except Exception:
        return False


@app.get("/api/m365/status")
async def m365_status():
    from integrations.m365_client import status as m365_status_fn
    import config as cfg_module
    st = m365_status_fn()
    st["enabled"] = cfg_module.config.get("m365_enabled", True)
    return st


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

    if update.github_sync_on_tasks is not None:
        current["github_sync_on_tasks"] = update.github_sync_on_tasks
        cfg_module.config["github_sync_on_tasks"] = update.github_sync_on_tasks

    if update.m365_enabled is not None:
        current["m365_enabled"] = update.m365_enabled
        cfg_module.config["m365_enabled"] = update.m365_enabled

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


@app.get("/api/search")
async def search_site(request: Request, q: str = "", limit: int = 30):
    """Глобальный поиск по задачам, проектам, чату и обучению."""
    from integrations.search_service import search_room
    from room.message_filter import is_privileged
    user = _optional_user(request)
    viewer = {
        "user_id": user.get("id", "") if user else "",
        "role": user.get("role", "guest") if user else "guest",
    }
    return search_room(
        q, room, limit=min(max(limit, 1), 100),
        user_id=viewer.get("user_id", ""),
        privileged=is_privileged(viewer.get("role", "")),
        viewer=viewer,
    )


@app.get("/api/sites/latest")
async def get_latest_site():
    """Готовый HTML-сайт от Сони"""
    site_file = os.path.join(os.path.dirname(__file__), "output", "sites", "latest.html")
    if os.path.exists(site_file):
        return FileResponse(site_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Сайт ещё не создан. Дайте Соне задачу со словом «сайт».")


@app.get("/api/tasks")
async def get_tasks(request: Request):
    """Журнал задач: свои задачи для пользователя, все — для admin."""
    from room.message_filter import is_privileged
    user = _optional_user(request)
    empty = {
        "stats": {"total": 0, "completed": 0, "active": 0, "awaiting_approval": 0, "failed": 0, "cancelled": 0},
        "tasks": [],
        "completed": [],
        "active": [],
    }
    if not user:
        return empty
    uid = user.get("id", "")
    if not is_privileged(user.get("role", "")):
        room.task_history.claim_orphans_for_user(
            uid, user.get("email", ""), user.get("name", "")
        )
    if is_privileged(user.get("role", "")):
        return {
            "stats": room.task_history.stats(),
            "tasks": room.task_history.get_all()[:100],
            "completed": room.task_history.get_completed()[:50],
            "active": room.task_history.get_active()[:30],
        }
    tasks = room.task_history.get_for_user(uid, 100)
    active_statuses = (
        "submitted", "queued", "in_progress", "triaging",
        "awaiting_approval", "revision_requested",
    )
    return {
        "stats": room.task_history.stats_for_user(uid),
        "tasks": tasks,
        "completed": [t for t in tasks if t.get("status") == "completed"][:50],
        "active": [t for t in tasks if t.get("status") in active_statuses][:30],
    }


@app.get("/api/dashboard")
async def get_dashboard(request: Request):
    """Сводка для Dashboard: команда, знания, интеграции."""
    import config as cfg_module
    from integrations.local_git_sync import get_status as git_status
    from room.message_filter import is_privileged, filter_agents_for_viewer

    user = _optional_user(request)
    viewer = {
        "user_id": user.get("id", "") if user else "",
        "role": user.get("role", "guest") if user else "guest",
    }
    privileged = is_privileged(viewer.get("role", ""))

    agents_data = []
    total_knowledge = 0
    for agent in room.agents.values():
        if not privileged and agent.agent_id == "security":
            continue
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

    agents_data = filter_agents_for_viewer(agents_data, viewer)
    git = git_status() if privileged else {}
    task_stats = (
        room.task_history.stats()
        if privileged
        else room.task_history.stats_for_user(viewer.get("user_id", ""))
    )
    return {
        "team_size": len(agents_data),
        "agents": agents_data,
        "total_knowledge": total_knowledge,
        "task_stats": task_stats,
        "figma_configured": _figma_is_configured() if privileged else False,
        "git_auto_sync": cfg_module.config.get("git_auto_sync", True) if privileged else False,
        "cursor_enabled": cfg_module.config.get("cursor_enabled", False) if privileged else False,
        "cursor_repo_url": cfg_module.config.get("cursor_repo_url", "") if privileged else "",
        "git": git,
    }


@app.get("/api/activity")
async def get_activity(request: Request, limit: int = 30):
    """Последние события рабочего канала для ленты активности."""
    from room.message_filter import filter_messages_for_viewer

    user = _optional_user(request)
    viewer = {
        "user_id": user.get("id", "") if user else "",
        "role": user.get("role", "guest") if user else "guest",
    }
    items = []
    for msg in reversed(filter_messages_for_viewer(room.work_history, viewer)[-limit * 2:]):
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


async def _bootstrap_figma_discovery(room_manager) -> None:
    """При старте — заполнить очередь из каталога/web_cache без ожидания фонового цикла."""
    import asyncio
    import config as cfg_module

    await asyncio.sleep(3)
    if not cfg_module.config.get("figma_study_enabled", True):
        return
    if not cfg_module.config.get("figma_auto_discover", True):
        return
    frontend = room_manager.agents.get("frontend")
    if not frontend:
        return
    try:
        from integrations.figma_discovery import run_discovery_scan

        scan = await run_discovery_scan(frontend, include_web=True)
        if scan.get("added"):
            print(f"🎨 Figma discovery: в очередь добавлено {scan['added']} макет(ов)")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Figma discovery bootstrap: %s", e)


async def _build_design_lab_payload() -> dict:
    """Полный ответ Дизайн-лаба — один источник для /api/figma/studio и /api/figma/design-lab."""
    from integrations.figma_discovery import enrich_discovery_status
    from integrations.figma_learning import get_studio_stats, load_patterns, load_portfolio

    stats = get_studio_stats()
    if stats.get("discovery"):
        stats["discovery"] = await enrich_discovery_status(dict(stats["discovery"]))
    patterns = load_patterns()
    frontend = room.agents.get("frontend")
    knowledge = []
    agent_state = {}
    if frontend:
        agent_state = {
            "status": frontend.status,
            "location": frontend.location,
            "figma_studies": getattr(frontend, "figma_studies", 0),
            "figma_creations": getattr(frontend, "figma_creations", 0),
        }
        design_sources = {"figma", "figma_auto", "figma_builtin", "figma_web", "figma_portfolio", "import"}
        for k in reversed(frontend.learned_topics):
            src = k.get("source") or ""
            topic = (k.get("topic") or "").lower()
            kws = k.get("keywords") or []
            if src in design_sources or "figma" in topic or "figma" in kws or "design" in kws:
                knowledge.append(k)
            if len(knowledge) >= 40:
                break
    return {
        **stats,
        "agent": agent_state,
        "knowledge": knowledge,
        "studied": patterns.get("studied", []),
        "color_palette": patterns.get("colors", [])[:32],
        "fonts": patterns.get("fonts", [])[:16],
        "frame_names": patterns.get("frames", [])[:20],
        "portfolio": load_portfolio()[:20],
        "recent_portfolio": stats.get("recent_portfolio") or load_portfolio()[:5],
    }


@app.get("/api/figma/status")
async def figma_status():
    from integrations.figma_oauth import get_connection_status
    return await get_connection_status()


@app.get("/api/figma/theme")
async def figma_theme_get():
    """Текущая Snow/Figma тема (JSON + путь к CSS)."""
    from integrations.figma_theme import ensure_theme_files, CSS_PATH
    theme = ensure_theme_files()
    return {
        "ok": True,
        "source": theme.get("source"),
        "updated_at": theme.get("updated_at"),
        "css_path": "/static/css/figma-theme.generated.css",
        "light": theme.get("light"),
        "dark": theme.get("dark"),
        "extracted": theme.get("extracted", {}),
    }


@app.post("/api/figma/theme/sync")
async def figma_theme_sync():
    """Синхронизация цветов из Figma Snow Dashboard → generated CSS."""
    from integrations.figma_theme import sync_from_figma, CSS_PATH
    from integrations.figma_rate_limit import FigmaRateLimitError
    try:
        theme = await sync_from_figma()
    except FigmaRateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e), headers={"Retry-After": str(int(e.retry_after))})
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {
        "ok": True,
        "source": theme.get("source"),
        "updated_at": theme.get("updated_at"),
        "css_path": "/static/css/figma-theme.generated.css",
        "extracted": theme.get("extracted", {}),
    }


@app.get("/api/rag/status")
async def rag_status():
    from integrations.rag.ingest import get_index_stats
    from knowledge_packs.packs_data import pack_stats
    stats = get_index_stats()
    return {"ok": True, "index": stats, "pack_catalog": pack_stats()}


@app.post("/api/rag/reindex")
async def rag_reindex(replace: bool = False):
    from integrations.rag.ingest import ingest_all_packs, get_index_stats
    result = ingest_all_packs(replace=replace)
    return {"ok": True, "ingest": result, "index": get_index_stats()}


@app.post("/api/rag/embed")
async def rag_embed(force: bool = False):
    from integrations.rag.embed_index import embed_all_chunks
    result = await embed_all_chunks(force=force)
    from integrations.rag.ingest import get_index_stats
    return {"ok": True, "embed": result, "index": get_index_stats()}


@app.get("/api/llm/status")
async def llm_status():
    from integrations.llm_client import is_configured, router_model, _settings
    from integrations.rag.embeddings import is_configured as emb_ok
    s = _settings()
    return {
        "ok": True,
        "llm_configured": is_configured(),
        "embeddings_configured": emb_ok(),
        "model": s.get("model"),
        "router_model": router_model(),
    }


class ToolInvokeRequest(BaseModel):
    agent_id: str = "pm"
    tool: str = "rag_search"
    arguments: dict = {}


@app.post("/api/tools/invoke")
async def tools_invoke(body: ToolInvokeRequest):
    from integrations.mcp_gateway import invoke_tool
    from integrations.agent_tools import tools_for
    if body.agent_id not in room.agents and body.agent_id not in tools_for(body.agent_id):
        raise HTTPException(status_code=404, detail="Unknown agent")
    result = await invoke_tool(body.agent_id, body.tool, body.arguments or {})
    return result


@app.get("/api/tools/{agent_id}")
async def tools_list(agent_id: str):
    from integrations.mcp_gateway import list_tools
    return {"agent_id": agent_id, "tools": await list_tools(agent_id)}


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
    """Studio + Design Lab (единый payload для совместимости UI)."""
    return await _build_design_lab_payload()


@app.get("/api/figma/design-lab")
@app.get("/api/design-lab")
async def figma_design_lab():
    """Дизайн-лаб Сони — паттерны, память, статистика."""
    return await _build_design_lab_payload()


@app.post("/api/figma/studio/study-url")
@app.post("/api/figma/study")
async def figma_study_url(body: FigmaStudyUrlRequest):
    """Соня изучает макет по URL и сохраняет в память."""
    from integrations.figma_learning import (
        study_reference_file,
        study_builtin_pattern,
        ensure_seed_patterns,
    )
    from integrations.figma_rate_limit import is_in_cooldown

    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL обязателен")

    ensure_seed_patterns()
    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")

    prev_status = frontend.status
    prev_loc = frontend.location
    frontend.status = "learning"
    frontend.location = "library"
    await room.send_agents_state()

    try:
        if is_in_cooldown():
            ok = await study_builtin_pattern(frontend)
            return {"ok": ok, "mode": "builtin", "message": "Локальный UI-референс (Figma API на паузе)"}

        result = await study_reference_file(frontend, url)
        if result and result.get("error"):
            err = str(result.get("error", ""))[:160]
            ok = await study_builtin_pattern(frontend)
            return {
                "ok": ok,
                "mode": "fallback",
                "error": err,
                "message": f"Figma API: {err}. Изучен встроенный паттерн.",
            }
        if result:
            frontend.figma_studies = getattr(frontend, "figma_studies", 0) + 1
            return {
                "ok": True,
                "mode": "figma",
                "knowledge": result.get("knowledge"),
                "summary": (result.get("result") or {}).get("summary"),
                "preview_url": (result.get("result") or {}).get("preview_url"),
            }
        ok = await study_builtin_pattern(frontend)
        return {"ok": ok, "mode": "builtin"}
    finally:
        frontend.status = prev_status if prev_status != "learning" else "idle"
        frontend.location = prev_loc if prev_loc else "studio"
        await room.send_agents_state()


@app.post("/api/figma/studio/trigger")
async def figma_studio_trigger(action: str = "study", request: Request = None):
    """Ручной запуск обучения/создания Сони в Studio."""
    from integrations.figma_learning import run_figma_study_session, ensure_seed_patterns

    ensure_seed_patterns()
    if action == "create":
        return await _sonya_agent_create_project(request)

    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")

    ok = await run_figma_study_session(frontend)
    if ok:
        frontend.figma_studies = getattr(frontend, "figma_studies", 0) + 1
    await room.send_agents_state()
    return {"ok": ok, "action": action}


@app.post("/api/figma/studio/discover")
async def figma_studio_discover(scan_only: bool = False):
    """Сканирование Figma-проектов и автономное изучение Соней."""
    from integrations.figma_discovery import run_discovery_scan, try_autonomous_study

    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")

    prev_status = frontend.status
    prev_loc = frontend.location
    scan = await run_discovery_scan(frontend, include_web=True)

    studied = False
    if not scan_only:
        frontend.status = "learning"
        frontend.location = "library"
        await room.send_agents_state()
        try:
            studied = await try_autonomous_study(frontend)
            if studied:
                frontend.figma_studies = getattr(frontend, "figma_studies", 0) + 1
        finally:
            frontend.status = prev_status if prev_status != "learning" else "idle"
            frontend.location = prev_loc if prev_loc else "studio"
            await room.send_agents_state()

    from integrations.figma_discovery import get_discovery_status, enrich_discovery_status

    discovery = await enrich_discovery_status(get_discovery_status())
    return {
        "ok": True,
        "scan": scan,
        "studied": studied,
        "discovery": discovery,
    }


# ─── Sonya Design Studio ───────────────────────────────────

async def _sonya_agent_create_project(request: Request = None):
    from integrations.sonya_studio import run_studio_create_session
    from integrations.sonya_studio_notify import notify_studio
    from room.subscriptions import can_access_view, access_denied_message

    if request:
        token = _get_session_token(request)
        from room.user_auth import get_user_from_token
        u = get_user_from_token(token)
        if u and not can_access_view(u, "sonya-studio"):
            raise HTTPException(status_code=403, detail=access_denied_message("sonya-studio", u))
        if u:
            _charge_or_forbid(u, "sonya_create")

    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")
    project = await run_studio_create_session(frontend)
    if not project:
        raise HTTPException(status_code=500, detail="Не удалось создать проект в Studio")
    frontend.figma_creations = getattr(frontend, "figma_creations", 0) + 1
    await notify_studio("project", project_title=project.get("title", ""), project_id=project.get("id", ""))
    await room.send_agents_state()
    return {"ok": True, "project": project}


@app.get("/api/sonya/projects")
async def sonya_list_projects():
    from integrations.sonya_studio import list_projects
    return {"projects": list_projects()}


@app.post("/api/sonya/projects")
async def sonya_create_project(body: SonyaProjectCreate, request: Request):
    from integrations.sonya_studio import create_project
    from room.user_auth import get_user_from_token

    user = get_user_from_token(_get_session_token(request))
    author = (user or {}).get("name") or (user or {}).get("email") or "Пользователь"
    project = create_project(
        title=body.title or "Новый проект",
        description=body.description,
        task=body.task or f"UI проект от {author}. Современный интерфейс, React.",
        created_by=author,
    )
    from integrations.sonya_studio_notify import notify_studio
    await notify_studio("project", project_title=project.get("title", ""), project_id=project.get("id", ""))
    return {"ok": True, "project": project}


@app.post("/api/sonya/projects/create-new")
async def sonya_create_new_by_agent(request: Request):
    return await _sonya_agent_create_project(request)


@app.post("/api/sonya/studio/create")
async def sonya_studio_create_alias(request: Request):
    """Алиас — статический путь без {project_id}, чтобы не ловить 404."""
    return await _sonya_agent_create_project(request)


@app.get("/api/sonya/projects/{project_id}")
async def sonya_get_project(project_id: str):
    from integrations.sonya_studio import get_project
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return project


@app.post("/api/sonya/projects/{project_id}/comments")
async def sonya_add_comment(project_id: str, body: SonyaCommentCreate, request: Request):
    from integrations.sonya_studio import add_comment, get_project
    from room.user_auth import get_user_from_token

    user = get_user_from_token(_get_session_token(request))
    author = (user or {}).get("name") or (user or {}).get("email") or "Пользователь"
    try:
        comment = add_comment(
            project_id,
            text=body.text,
            author=author,
            x=body.x,
            y=body.y,
            frame_id=body.frame_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not comment:
        raise HTTPException(status_code=404, detail="Проект не найден")
    project = get_project(project_id)
    from integrations.sonya_studio_notify import notify_studio
    await notify_studio(
        "comment",
        project_title=project.get("title", ""),
        project_id=project_id,
        author=author,
        text=body.text,
        open_comments=project.get("open_comments", 0),
    )
    return {"ok": True, "comment": comment, "project": project}


@app.post("/api/sonya/projects/{project_id}/apply-comments")
async def sonya_apply_comments(project_id: str):
    """Соня применяет открытые комментарии — новая версия."""
    from integrations.sonya_studio import apply_open_comments, get_project

    frontend = room.agents.get("frontend")
    if not frontend:
        raise HTTPException(status_code=404, detail="Соня не найдена")
    try:
        project = await apply_open_comments(frontend, project_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    from integrations.sonya_studio_notify import notify_studio
    ver = project.get("current_version") or {}
    await notify_studio(
        "version",
        project_title=project.get("title", ""),
        project_id=project_id,
        version_num=ver.get("version_num", 1),
    )
    await room.send_agents_state()
    return {"ok": True, "project": project}


@app.get("/api/sonya/projects/{project_id}/diff")
async def sonya_project_diff(project_id: str, from_ref: str = "1", to_ref: str = ""):
    from integrations.sonya_studio_export import compare_versions
    from integrations.sonya_studio import get_project

    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")
    versions = project.get("versions") or []
    if not to_ref:
        to_ref = str((project.get("current_version") or {}).get("version_num") or len(versions))
    diff = compare_versions(project_id, from_ref, to_ref)
    if not diff:
        raise HTTPException(status_code=400, detail="Не удалось сравнить версии")
    return diff


@app.get("/api/sonya/projects/{project_id}/handoff")
async def sonya_project_handoff(project_id: str):
    from integrations.sonya_studio_export import build_handoff_package

    pkg = build_handoff_package(project_id)
    if not pkg:
        raise HTTPException(status_code=404, detail="Проект не найден")
    return pkg


@app.get("/api/sonya/projects/{project_id}/handoff/download")
async def sonya_project_handoff_download(project_id: str):
    from integrations.sonya_studio_export import build_handoff_zip

    result = build_handoff_zip(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Проект не найден")
    filename, data = result
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/sonya/projects/{project_id}/publish")
async def sonya_publish(project_id: str, body: SonyaPublishRequest):
    from integrations.sonya_studio import publish_project, get_project

    project = publish_project(project_id, figma_url=body.figma_url)
    if not project:
        raise HTTPException(status_code=404, detail="Проект не найден")

    frontend = room.agents.get("frontend")
    if frontend and frontend.room_manager:
        handoff = project.get("figma_handoff") or {}
        await frontend.room_manager.broadcast_work({
            "type": "sonya_studio_published",
            "agent_id": "frontend",
            "agent_name": frontend.name,
            "agent_emoji": frontend.emoji,
            "project_id": project_id,
            "project_title": project.get("title"),
            "message": (
                f"📦 **Опубликовано** · «{project.get('title')}» v{handoff.get('version_num', 1)}\n"
                f"Tokens и React-код готовы к handoff в Figma"
            ),
            "handoff": handoff,
            "timestamp": handoff.get("published_at"),
        })

    from integrations.sonya_studio_notify import notify_studio
    await notify_studio(
        "published",
        project_title=project.get("title", ""),
        project_id=project_id,
        version_num=(project.get("figma_handoff") or {}).get("version_num", 1),
    )

    return {"ok": True, "project": project}


@app.post("/api/figma/import")
async def figma_import(request: FigmaImportRequest):
    """Импорт макета из Figma по URL."""
    from integrations.figma_client import get_client_async, parse_figma_url

    if not request.url.strip():
        raise HTTPException(status_code=400, detail="URL обязателен")
    parsed = parse_figma_url(request.url)
    if not parsed:
        raise HTTPException(status_code=400, detail="Некорректная ссылка Figma")

    client = await get_client_async()
    if not client.configured:
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
        from integrations.figma_learning import remember_figma_from_import
        await remember_figma_from_import(frontend, result, request.url.strip())

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
async def get_timeline_replay(request: Request, hours: float = 1.0):
    from integrations.timeline_store import replay_summary
    from room.message_filter import filter_messages_for_viewer, is_privileged

    user = _optional_user(request)
    viewer = {
        "user_id": user.get("id", "") if user else "",
        "role": user.get("role", "guest") if user else "guest",
    }
    data = replay_summary(hours=min(max(hours, 0.25), 24))
    if is_privileged(viewer.get("role", "")):
        return data
    events = filter_messages_for_viewer(data.get("events") or [], viewer)
    by_type = {}
    for e in events:
        t = e.get("type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
    return {**data, "total": len(events), "by_type": by_type, "events": events[-80:]}


@app.get("/api/kanban")
async def get_kanban(request: Request):
    from room.message_filter import is_privileged
    user = _optional_user(request)
    uid = user.get("id", "") if user else ""
    privileged = is_privileged(user.get("role", "")) if user else False
    tasks = room.task_history.get_all() if privileged else room.task_history.get_for_user(uid, 200)
    columns = {"submitted": [], "in_progress": [], "completed": [], "failed": []}
    for task in tasks:
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


@app.get("/api/projects/{artifact_id}/file/{filename}")
async def project_file_download(artifact_id: str, filename: str):
    import os
    from room.artifact_store import get_artifact, ARTIFACTS_DIR
    art = get_artifact(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="Not found")
    finfo = (art.get("files") or {}).get(filename)
    if not finfo or not isinstance(finfo, dict) or not finfo.get("binary"):
        raise HTTPException(status_code=404, detail="File not found")
    safe = os.path.basename(filename)
    path = os.path.join(ARTIFACTS_DIR, artifact_id, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File missing on disk")
    media = {
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
    }
    ext = os.path.splitext(safe)[1].lower()
    return FileResponse(path, media_type=media.get(ext, "application/octet-stream"), filename=safe)


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
async def get_sprint_api(request: Request):
    from room.sprint_store import get_sprint
    user = _optional_user(request)
    if not user:
        return {"active": False, "guest": True, "backlog": [], "stats": {"total": 0, "done": 0, "todo": 0}}
    return get_sprint(user.get("id", ""))


class SprintStart(BaseModel):
    name: str
    goal: str
    days: int = 7


@app.post("/api/sprint/start")
async def start_sprint_api(body: SprintStart, request: Request):
    user = _current_user(request)
    from room.sprint_store import start_sprint
    return start_sprint(body.name, body.goal, body.days, user.get("id", ""))


class SprintBacklogItem(BaseModel):
    text: str
    priority: str = "medium"


@app.post("/api/sprint/backlog")
async def add_sprint_backlog(body: SprintBacklogItem, request: Request):
    user = _current_user(request)
    from room.sprint_store import add_backlog_item
    return add_backlog_item(body.text, body.priority, user.get("id", ""))


@app.post("/api/sprint/backlog/{item_id}/toggle")
async def toggle_sprint_item(item_id: str, request: Request):
    user = _current_user(request)
    from room.sprint_store import toggle_backlog
    return toggle_backlog(item_id, user_id=user.get("id", ""))


@app.post("/api/sprint/end")
async def end_sprint_api(request: Request):
    user = _current_user(request)
    from room.sprint_store import end_sprint
    return end_sprint(user.get("id", ""))


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
async def create_view_token(request: Request, hours: int = 72, label: str = "client", nda: bool = False):
    user = _optional_user(request)
    if user:
        from room.user_auth import has_privilege
        if not has_privilege(user, "view_link") and user.get("role") not in ("owner", "admin", "tech_admin"):
            raise HTTPException(status_code=403, detail="View-link недоступен на вашем тарифе")
    from room.view_tokens import create_token
    scope = "investor" if nda else "view"
    t = create_token(hours=hours, label=label, scope=scope, nda_required=nda)
    return {"ok": True, "url": f"/investor?view={t['token']}", **t}


@app.get("/api/view-token/validate")
async def validate_view_token(token: str = "", accept_nda: bool = False):
    from room.view_tokens import validate_token
    result = validate_token(token, accept_nda=accept_nda)
    if not result:
        raise HTTPException(status_code=404, detail="Invalid or expired token")
    return result


class TaskPriorityUpdate(BaseModel):
    priority: str


class TaskApprovalBody(BaseModel):
    note: str = ""


class TaskRevisionBody(BaseModel):
    feedback: str


@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, request: Request, body: TaskApprovalBody = TaskApprovalBody()):
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not room.task_history.user_owns_task(task_id, user["id"], is_privileged(user.get("role"))):
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    ok = await room.approve_task(task_id, body.note or "")
    if not ok:
        raise HTTPException(status_code=400, detail="Task not awaiting approval")
    return {"ok": True, "task_id": task_id}


@app.post("/api/tasks/{task_id}/revision")
async def request_task_revision(task_id: str, request: Request, body: TaskRevisionBody):
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not room.task_history.user_owns_task(task_id, user["id"], is_privileged(user.get("role"))):
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    if not (body.feedback or "").strip():
        raise HTTPException(status_code=400, detail="Feedback required")
    ok = await room.request_task_revision(task_id, body.feedback.strip())
    if not ok:
        raise HTTPException(status_code=400, detail="Task not awaiting approval")
    return {"ok": True, "task_id": task_id}


@app.post("/api/tasks/cancel-all")
async def cancel_all_tasks(request: Request):
    """Отменить активные задачи (свои — пользователь, все — admin)."""
    from room.message_filter import is_privileged
    user = _current_user(request)
    count = await room.cancel_all_tasks(
        user_id=user.get("id", ""),
        privileged=is_privileged(user.get("role")),
    )
    return {"ok": True, "cancelled": count}


@app.post("/api/tasks/clear")
async def clear_tasks_history(request: Request):
    """Полностью очистить журнал задач (только admin)."""
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not is_privileged(user.get("role")):
        raise HTTPException(status_code=403, detail="Только для администраторов")
    total = await room.clear_task_history()
    return {"ok": True, "cleared": total}


@app.patch("/api/tasks/{task_id}/priority")
async def update_task_priority(task_id: str, body: TaskPriorityUpdate, request: Request):
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not room.task_history.user_owns_task(task_id, user["id"], is_privileged(user.get("role"))):
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    ok = room.task_history.set_priority(task_id, body.priority)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    await room._broadcast_task_history()
    return {"ok": True}


@app.get("/api/mentions/aliases")
async def mention_aliases():
    from room.mention_parser import list_aliases
    return {"aliases": list_aliases()}


@app.get("/api/chat/commands")
async def chat_slash_commands():
    from room.slash_commands import list_commands, help_text
    return {"commands": list_commands(), "help": help_text()}


@app.get("/api/learning/masha-lab")
async def masha_learning_lab():
    return room._learning_store().get_dashboard()


class LearningSubmitBody(BaseModel):
    title: str = ""
    description: str = ""
    collaborative: bool = False


@app.post("/api/learning/submit")
async def submit_learning_exercise(body: LearningSubmitBody, request: Request):
    user = _optional_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    text = (body.description or body.title or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")
    await room._handle_learning_command({
        "cmd": "collab" if body.collaborative else "learn",
        "text": text,
        "collaborative": body.collaborative,
        "learning_mode": True,
        "msg_type": "learning",
    })
    return {"ok": True, "dashboard": room._learning_store().get_dashboard()}


# ─── Investor Portal ─────────────────────────────────────────

@app.get("/api/investor/dashboard")
async def investor_dashboard(request: Request):
    user = _current_user(request)
    from room.message_filter import is_privileged
    if not (is_privileged(user.get("role", "")) or user.get("is_investor") or user.get("can_view_investor_portal")):
        raise HTTPException(status_code=403, detail="Investor Portal недоступен")
    stats = room.task_history.stats()
    learning = room._learning_store().get_dashboard()
    from room.security_monitor import get_monitor
    sec = get_monitor().dashboard()
    agents_state = [a.get_state() for a in room.agents.values()]
    return {
        "metrics": {
            "tasks_total": stats.get("total", 0),
            "tasks_completed": stats.get("completed", 0),
            "tasks_active": stats.get("active", 0),
            "agents_count": len(agents_state),
            "agents_active": sum(1 for a in agents_state if a.get("status") == "working"),
            "evaluations": learning.get("stats", {}).get("evaluations_count", 0),
            "average_score": learning.get("stats", {}).get("average_score", 0),
            "security_events_24h": sec.get("stats", {}).get("total_events", 0),
        },
        "agents": [{"id": a.get("agent_id"), "name": a.get("name"), "emoji": a.get("emoji"), "status": a.get("status")} for a in agents_state],
        "recent_tasks": room.task_history.get_all()[:15],
        "evaluations": learning.get("evaluations", [])[:10],
        "skill_matrix": room._learning_store().get_skill_matrix(),
    }


# ─── Security & Audit ────────────────────────────────────────

@app.get("/api/security/dashboard")
async def security_dashboard(request: Request):
    _current_user(request)
    from room.user_auth import can_access_admin
    user = _optional_user(request)
    if not can_access_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    from room.security_monitor import get_monitor
    from room import audit_log
    return {
        **get_monitor().dashboard(),
        "audit_stats": audit_log.stats(),
        "audit_recent": audit_log.get_recent(50),
    }


@app.get("/api/audit/log")
async def audit_log_api(request: Request, limit: int = 100, severity: str = ""):
    from room.user_auth import can_access_admin
    user = _current_user(request)
    if not can_access_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    from room import audit_log
    return {"entries": audit_log.get_recent(limit, severity), "stats": audit_log.stats()}


@app.post("/api/security/unblock/{ip}")
async def security_unblock_ip(ip: str, request: Request):
    from room.user_auth import can_access_admin
    user = _current_user(request)
    if not can_access_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    from room.security_monitor import get_monitor
    monitor = get_monitor()
    if ip in monitor._blocks:
        del monitor._blocks[ip]
        monitor._save_blocks()
    from room import audit_log
    audit_log.log_event("ip_unblocked", user_id=user["id"], ip=ip, severity="info")
    return {"ok": True}


# ─── Task Templates & Workspaces ─────────────────────────────

@app.get("/api/task-templates")
async def list_task_templates(category: str = ""):
    from room.task_templates import list_templates
    return {"templates": list_templates(category)}


@app.post("/api/task-templates/{template_id}/apply")
async def apply_task_template(template_id: str, request: Request):
    user = _current_user(request)
    from room.task_templates import get_template
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    _charge_or_forbid(user, "task")
    text = tpl["description"]
    if tpl.get("learning"):
        await room._handle_learning_command({
            "cmd": "collab" if "collab" in template_id else "learn",
            "text": text,
            "collaborative": "collab" in template_id,
            "learning_mode": True,
            "msg_type": "learning",
        })
    else:
        await room.handle_user_message({"type": "task", "text": text, "target": "all"})
    from room import audit_log
    audit_log.log_event("template_applied", user_id=user["id"], detail=template_id)
    return {"ok": True, "template": tpl}


@app.get("/api/workspaces")
async def list_workspaces(request: Request):
    user = _current_user(request)
    from room.workspaces import list_for_user
    return {"workspaces": list_for_user(user["id"])}


class WorkspaceCreate(BaseModel):
    name: str = ""
    description: str = ""


@app.post("/api/workspaces")
async def create_workspace(body: WorkspaceCreate, request: Request):
    user = _current_user(request)
    from room.workspaces import create
    ws = create(body.name, user["id"], body.description)
    return {"ok": True, "workspace": ws}


# ─── Feature Flags ───────────────────────────────────────────

@app.get("/api/feature-flags")
async def get_feature_flags():
    from room.feature_flags import get_flags
    from integrations.stripe_billing import is_configured
    flags = get_flags()
    if is_configured():
        flags["stripe_billing"] = True
    return {"flags": flags}


class FlagUpdate(BaseModel):
    name: str
    value: bool


@app.post("/api/admin/feature-flags")
async def update_feature_flag(body: FlagUpdate, request: Request):
    user = _current_user(request)
    from room.user_auth import has_privilege
    if not has_privilege(user, "manage_settings") and user.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Forbidden")
    from room.feature_flags import set_flag
    return {"flags": set_flag(body.name, body.value, user)}


@app.get("/api/learning/skill-matrix")
async def learning_skill_matrix():
    return room._learning_store().get_skill_matrix()


# ─── Notifications ─────────────────────────────────────────────

@app.get("/api/notifications")
async def list_notifications(request: Request):
    user = _optional_user(request)
    from room import notifications
    uid = user.get("id", "") if user else ""
    return {
        "items": notifications.list_for_user(uid),
        "unread": notifications.unread_count(uid),
    }


class NotifReadBody(BaseModel):
    id: str


@app.post("/api/notifications/read")
async def mark_notification_read(body: NotifReadBody, request: Request):
    user = _optional_user(request)
    from room import notifications
    uid = user.get("id", "") if user else ""
    ok = notifications.mark_read(body.id, uid)
    return {"ok": ok}


# ─── Dashboard layout ────────────────────────────────────────

@app.get("/api/dashboard/layout")
async def get_dashboard_layout(request: Request):
    user = _optional_user(request)
    from room.dashboard_layout import get_layout
    return get_layout(user.get("id", "") if user else "")


class DashboardLayoutBody(BaseModel):
    widgets: list[str] = []
    hidden: list[str] = []


@app.post("/api/dashboard/layout")
async def save_dashboard_layout(body: DashboardLayoutBody, request: Request):
    user = _optional_user(request)
    from room.dashboard_layout import save_layout
    uid = user.get("id", "") if user else "default"
    return {"ok": True, "layout": save_layout(uid, body.widgets, body.hidden)}


# ─── Task comments ───────────────────────────────────────────

class TaskCommentBody(BaseModel):
    text: str = ""


@app.get("/api/tasks/{task_id}/comments")
async def get_task_comments(task_id: str, request: Request):
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not room.task_history.user_owns_task(task_id, user["id"], is_privileged(user.get("role"))):
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    return {"comments": room.task_history.get_comments(task_id)}


@app.post("/api/tasks/{task_id}/comments")
async def add_task_comment(task_id: str, body: TaskCommentBody, request: Request):
    from room.message_filter import is_privileged
    user = _current_user(request)
    if not room.task_history.user_owns_task(task_id, user["id"], is_privileged(user.get("role"))):
        raise HTTPException(status_code=403, detail="Нет доступа к этой задаче")
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text required")
    c = room.task_history.add_comment(
        task_id, text,
        user_id=user.get("id", ""),
        user_name=user.get("name") or user.get("email", "User").split("@")[0],
    )
    if not c:
        raise HTTPException(status_code=404, detail="Task not found")
    await room._broadcast_task_history()
    return {"ok": True, "comment": c}


# ─── Workspaces extended ─────────────────────────────────────

class WorkspaceSwitchBody(BaseModel):
    workspace_id: str = ""


@app.post("/api/workspaces/active")
async def set_active_workspace(body: WorkspaceSwitchBody, request: Request):
    user = _current_user(request)
    from room.workspaces import set_active, list_for_user
    ws_list = list_for_user(user["id"])
    if body.workspace_id and not any(w.get("id") == body.workspace_id for w in ws_list):
        raise HTTPException(status_code=404, detail="Workspace not found")
    set_active(user["id"], body.workspace_id)
    return {"ok": True, "active_id": body.workspace_id}


@app.get("/api/workspaces/active")
async def get_active_workspace(request: Request):
    user = _optional_user(request)
    if not user:
        return {"active_id": ""}
    from room.workspaces import get_active, list_for_user
    aid = get_active(user["id"])
    return {"active_id": aid, "workspaces": list_for_user(user["id"])}


# ─── Investor digest ─────────────────────────────────────────

@app.post("/api/investor/digest")
async def send_investor_digest(request: Request):
    from room.user_auth import can_access_admin
    user = _current_user(request)
    if not can_access_admin(user):
        raise HTTPException(status_code=403, detail="Forbidden")
    stats = room.task_history.stats()
    learning = room._learning_store().get_dashboard()
    from room import notifications
    body = (
        f"Задач: {stats.get('completed', 0)} выполнено, "
        f"{stats.get('active', 0)} в работе. "
        f"Средняя оценка Маши: {learning.get('stats', {}).get('average_score', '—')}/10"
    )
    notifications.push("📊 Weekly Investor Update", body, ntype="investor", link="/investor")
    return {"ok": True, "digest": body}


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
    """WebSocket — auth через cookie; guest read-only."""
    from room.user_auth import get_user_from_token, SESSION_COOKIE
    from room.feature_flags import is_enabled
    from room.view_tokens import validate_token

    token = websocket.cookies.get(SESSION_COOKIE, "")
    user = get_user_from_token(token) if token else None
    view_tok = websocket.query_params.get("view_token", "")
    view_access = validate_token(view_tok) if view_tok else None
    guest_readonly = is_enabled("guest_readonly_ws") and not user and not (view_access and view_access.get("valid"))

    await room.connect(websocket, user=user, view_token=view_access, readonly=guest_readonly)
    try:
        while True:
            data = await websocket.receive_text()
            if guest_readonly:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "🔒 Войдите для отправки задач",
                    "timestamp": __import__("datetime").datetime.now().isoformat(),
                }, ensure_ascii=False))
                continue
            if user and user.get("role") == "investor":
                try:
                    message = json.loads(data)
                    if message.get("type") in ("task", "learning"):
                        await websocket.send_text(json.dumps({
                            "type": "error",
                            "message": "🔒 Investor — только просмотр",
                        }, ensure_ascii=False))
                        continue
                except json.JSONDecodeError:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "🔒 Investor — только просмотр",
                    }, ensure_ascii=False))
                    continue
            try:
                message = json.loads(data)
                meta = room.connection_meta.get(websocket, {})
                await room.handle_user_message(message, user=user, connection_meta=meta)
            except json.JSONDecodeError:
                meta = room.connection_meta.get(websocket, {})
                await room.handle_user_message({
                    "type": "task",
                    "text": data,
                    "target": "all"
                }, user=user, connection_meta=meta)
    except WebSocketDisconnect:
        await room.disconnect(websocket)
    except Exception:
        await room.disconnect(websocket)
