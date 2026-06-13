"""
AI Team Room — десктоп-приложение.

Режимы:
  python desktop.py              — клиент к облачному серверу (по умолчанию)
  python desktop.py --local      — встроенный локальный сервер + окно
  python desktop.py --server URL — указать адрес сервера
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if getattr(sys, "frozen", False):
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    os.chdir(APP_DIR)
else:
    APP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(APP_DIR))

DEFAULT_SERVER = os.environ.get("AI_TEAM_SERVER", "http://80.78.245.66").rstrip("/")
CONFIG_DIR = Path.home() / ".ai-team-room"
CONFIG_FILE = CONFIG_DIR / "config.json"
APP_VERSION = os.environ.get("DESKTOP_APP_VERSION", "1.0.0")


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("server"):
                return data
        except Exception:
            pass
    return {"server": DEFAULT_SERVER, "version": APP_VERSION}


def save_config(server: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(
        json.dumps({"server": server.rstrip("/"), "version": APP_VERSION}, indent=2),
        encoding="utf-8",
    )


def parse_args():
    local = "--local" in sys.argv
    server = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--server", "-s") and i + 1 < len(sys.argv):
            server = sys.argv[i + 1].strip().rstrip("/")
    return local, server


def run_local_server(host: str, port: int):
    import uvicorn
    uvicorn.run("app:app", host=host, port=port, reload=False, log_level="warning")


def wait_for_server(url: str, timeout: int = 20) -> bool:
    import urllib.request
    for _ in range(timeout * 10):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


class DesktopApi:
    """JS API для pywebview — открытие браузера и настройки."""

    def __init__(self, server: str):
        self._server = server

    def get_server(self) -> str:
        return self._server

    def set_server(self, url: str) -> bool:
        url = (url or "").strip().rstrip("/")
        if not url.startswith("http"):
            return False
        self._server = url
        save_config(url)
        return True

    def open_external(self, url: str):
        webbrowser.open(url)

    def get_version(self) -> str:
        return APP_VERSION


def start_window(server: str, local_mode: bool = False):
    try:
        import webview  # type: ignore
    except ImportError:
        print("pywebview не установлен. Открываю в браузере…")
        webbrowser.open(f"{server}/desktop?app=1")
        input("Нажмите Enter для выхода…")
        return

    entry_url = f"{server}/desktop?app=1&v={APP_VERSION.replace('.', '')}"
    api = DesktopApi(server)

    window = webview.create_window(
        title="AI Team Room",
        url=entry_url,
        width=1280,
        height=840,
        min_size=(960, 640),
        text_select=True,
        confirm_close=True,
        js_api=api,
    )

    def on_loaded():
        # После handoff/workspace навигация остаётся в том же окне
        pass

    webview.start(on_loaded, debug=False)


def start_local_desktop():
    from config import config
    host = "127.0.0.1"
    port = int(config.get("port", 8000))
    url = f"http://{host}:{port}"
    threading.Thread(target=run_local_server, args=(host, port), daemon=True).start()
    print("⏳ Запуск локального AI Team Room…")
    if not wait_for_server(url):
        print("❌ Сервер не поднялся.")
        webbrowser.open(url)
        input("Enter для выхода…")
        return
    start_window(url, local_mode=True)


def start_cloud_desktop(server: str | None = None):
    cfg = load_config()
    base = (server or cfg.get("server") or DEFAULT_SERVER).rstrip("/")
    save_config(base)
    print(f"🚀 AI Team Room Desktop → {base}")
    start_window(base)


def main():
    local, server = parse_args()
    if local:
        start_local_desktop()
    else:
        start_cloud_desktop(server)


if __name__ == "__main__":
    main()
