# AI Team Room (AI_team_takura)

FastAPI + WebSocket web app simulating a virtual team of 8 AI agents in a Three.js 3D studio. See `README.md` for the product overview.

## Cursor Cloud specific instructions

### Services & how to run
- Single service: a FastAPI/uvicorn web server. Run it with the project venv: `.venv/bin/python main.py` (serves on `http://localhost:8000`, host `0.0.0.0`). `main.py` is the web entry point used for development.
- Dependencies live in a virtualenv at `.venv` (gitignored). The startup update script creates/refreshes it; activate with `. .venv/bin/activate` or call binaries directly via `.venv/bin/...`.
- `config.json` controls `host`/`port`/learning settings; `debug: true` enables uvicorn auto-reload.

### Non-obvious caveats
- The frontend loads Three.js + OrbitControls from a CDN (`cdn.jsdelivr.net`), and the agents' self-learning loop periodically fetches external sites (dev.to, Wikipedia, etc.). Internet access is required for the 3D scene and learning to work; without it the UI still loads but the 3D view and learning will be degraded.
- `desktop.py` is an optional native-window mode that needs `pywebview` + system GUI libraries (GTK/Qt). It is NOT needed for development — use `main.py` (web mode) instead. The `pywebview` pip package installs fine headless; only its runtime desktop window needs GUI libs.
- Runtime data is written to gitignored dirs (`data/`, `knowledge/`, `direct_chats/`, `output/`). These are created automatically; safe to delete to reset state.

### Tests / lint / build
- There is no automated test suite and no linter config in this repo. The "QA"/"reviewer" behavior is simulated in-app by agents, not real pytest tests. A reasonable smoke check is `.venv/bin/python -m compileall -q agents room *.py`.
- "Build" (`build.bat` / `build.spec`) is a Windows-only PyInstaller `.exe` packaging step and is not relevant to the Linux dev environment.

### Core flow to exercise the app
- Assign a task via REST: `POST /api/task` with JSON `{"text": "...", "target": "all"}`, or via the WebSocket at `/ws`, or by typing in the "Рабочий чат" input in the UI. PM agent «Виктор» decomposes it and delegates subtasks; progress is visible at `GET /api/tasks` and in the UI "Задачи" tab.
