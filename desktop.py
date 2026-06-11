"""
Десктоп-версия AI Team Room.
Запускает FastAPI-сервер в фоне и открывает нативное окно приложения.
"""
import sys
import os
import threading
import time
import webbrowser

# Настройка кодировки для Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Определяем корень приложения (работает и в .exe PyInstaller)
if getattr(sys, 'frozen', False):
    APP_DIR = sys._MEIPASS
    os.chdir(APP_DIR)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, APP_DIR)

from config import config

HOST = "127.0.0.1"
PORT = config.get("port", 8000)
URL  = f"http://{HOST}:{PORT}"


def run_server():
    """Запуск FastAPI-сервера в фоновом потоке."""
    import uvicorn
    # Перегружаем host на localhost для безопасности десктоп-режима
    uvicorn.run(
        "app:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="warning",
    )


def wait_for_server(timeout: int = 15) -> bool:
    """Ждём, пока сервер поднимется."""
    import urllib.request
    for _ in range(timeout * 10):
        try:
            urllib.request.urlopen(URL, timeout=1)
            return True
        except Exception:
            time.sleep(0.1)
    return False


def start_desktop():
    """Основная точка входа для десктоп-приложения."""

    # 1. Запускаем сервер в фоне
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    print("⏳ Запуск AI Team Room…")
    if not wait_for_server():
        print("❌ Сервер не смог запуститься. Открываю браузер…")
        webbrowser.open(URL)
        input("Нажмите Enter для выхода…")
        return

    print("✅ Сервер запущен!")

    # 2. Пробуем открыть через pywebview (нативное окно)
    try:
        import webview  # type: ignore

        window = webview.create_window(
            title="AI Team Room",
            url=URL,
            width=1280,
            height=800,
            min_size=(900, 600),
            text_select=True,
            confirm_close=True,
        )

        # Опционально — скрываем рамку меню браузера (чистый вид)
        webview.start(debug=False)

    except ImportError:
        # pywebview не установлен — открываем в браузере
        print("ℹ️  pywebview не установлен. Открываю в браузере…")
        print(f"   Адрес: {URL}")
        webbrowser.open(URL)

        # Держим процесс живым пока браузер работает
        try:
            print("   Нажмите Ctrl+C для выхода.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("👋 Завершение работы…")

    except Exception as e:
        print(f"❌ Ошибка окна: {e}")
        webbrowser.open(URL)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    start_desktop()
