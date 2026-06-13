# AGENTS.md

## Cursor Cloud specific instructions

This is a self-contained Python FastAPI app ("AI Team Room") — a single web service with no database, auth, or external API keys. Agents are simulated locally; learning sources are public web endpoints (no credentials).

### Running
- Dependencies are installed into a virtualenv at `.venv` by the update script. Always use the venv interpreter, e.g. `.venv/bin/python main.py` (not bare `python`).
- `python main.py` starts uvicorn on `http://0.0.0.0:8000` (port from `config.json`). This is the dev entrypoint; `reload` follows `debug` in `config.json` (currently `false`).
- `desktop.py` is a native-window (pywebview) wrapper that needs a GUI/GTK+WebKit and is not usable headless — use `main.py` for cloud/dev.
- The server runs in the foreground; start it under tmux for background use.

### Testing / lint
- There is no automated test suite, lint config, or CI in this repo. Use `.venv/bin/python -m py_compile <files>` for a quick syntax sanity check.
- Quick functional check without a browser: `curl localhost:8000/api/agents`, then `POST /api/task` with `{"text": "...", "target": "all"}`, then poll `GET /api/tasks`.

### Known caveats
- The frontend agent "Соня" (React preview, `agents/react_preview.py` / `agents/frontend_dev.py`) can fail a task with `unexpected '{' in field name` — a pre-existing string-formatting bug in preview generation, unrelated to environment setup. Other agents and PM orchestration complete normally.
