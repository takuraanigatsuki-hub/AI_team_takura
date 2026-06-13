"""
AI Team Room — установщик для Windows.
Копирует AI_Team_Room.exe в %LOCALAPPDATA%\\Programs\\AI Team Room\\
и создаёт ярлык на рабочем столе.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass

APP_NAME = "AI Team Room"
EXE_NAME = "AI_Team_Room.exe"


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path.cwd()))
    return Path(__file__).resolve().parent / "dist"


def install_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", Path.home())) / "Programs" / APP_NAME


def find_source_exe() -> Path:
    root = resource_root()
    candidate = root / EXE_NAME
    if candidate.is_file():
        return candidate
    sibling = Path(sys.executable).resolve().parent / EXE_NAME
    if sibling.is_file():
        return sibling
    raise FileNotFoundError(f"Не найден {EXE_NAME} рядом с установщиком")


def create_shortcut(target: Path, shortcut_path: Path):
    ps = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
$Shortcut.TargetPath = '{target}'
$Shortcut.WorkingDirectory = '{target.parent}'
$Shortcut.Description = '{APP_NAME}'
$Shortcut.Save()
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def show_message(title: str, text: str):
    if sys.platform != "win32":
        print(text)
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    except Exception:
        print(text)


def main():
    try:
        src = find_source_exe()
    except FileNotFoundError as e:
        show_message(APP_NAME, str(e))
        return 1

    dest = install_dir()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / EXE_NAME

    try:
        shutil.copy2(src, target)
    except Exception as e:
        show_message(APP_NAME, f"Ошибка копирования:\n{e}")
        return 1

    desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop" / f"{APP_NAME}.lnk"
    if desktop.parent.exists():
        create_shortcut(target, desktop)

    start_menu = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    if start_menu.exists():
        create_shortcut(target, start_menu / f"{APP_NAME}.lnk")

    show_message(
        APP_NAME,
        f"Установка завершена!\n\nПапка:\n{dest}\n\nЯрлык создан на рабочем столе.\nСейчас откроется приложение.",
    )

    try:
        os.startfile(str(target))  # type: ignore[attr-defined]
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
