@echo off
chcp 65001 > nul
echo.
echo ╔══════════════════════════════════════╗
echo ║   Сборка AI Team Room в .exe         ║
echo ╚══════════════════════════════════════╝
echo.

:: Генерируем иконки
echo [1/4] Генерация иконок...
python make_icons.py
if %errorlevel% neq 0 (
    echo ОШИБКА: не удалось создать иконки
    pause
    exit /b 1
)

:: Устанавливаем зависимости
echo.
echo [2/4] Установка зависимостей...
pip install pywebview pyinstaller Pillow --quiet
if %errorlevel% neq 0 (
    echo ОШИБКА: не удалось установить зависимости
    pause
    exit /b 1
)

:: Пересоздаём иконки через Pillow
echo.
echo [3/4] Пересоздание иконок (с Pillow)...
python make_icons.py

:: Собираем .exe
echo.
echo [4/4] Сборка .exe через PyInstaller...
pyinstaller build.spec --clean --noconfirm
if %errorlevel% neq 0 (
    echo ОШИБКА: сборка не удалась
    pause
    exit /b 1
)

echo.
echo ══════════════════════════════════════════
echo  ✅ Готово! Файл: dist\AI_Team_Room.exe
echo ══════════════════════════════════════════
echo.
pause
