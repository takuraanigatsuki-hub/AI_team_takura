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
    DevOpsAgent, PMOrchestratorAgent
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
    ]

    # Регистрируем всех агентов
    for agent in agents:
        room.register_agent(agent)

    room.task_history.cleanup_stale(max_minutes=30)

    # Запускаем агентов
    await room.start_all_agents()

    # Запускаем периодическую рассылку состояния
    state_task = asyncio.create_task(room.state_broadcaster())

    print("🚀 AI Team Room запущен!")
    print("📡 Открой браузер: http://localhost:8000")

    yield  # Приложение работает

    # Остановка
    state_task.cancel()
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
