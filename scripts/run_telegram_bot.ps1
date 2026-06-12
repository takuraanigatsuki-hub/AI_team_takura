# Запуск standalone Telegram-бота (main.py должен быть уже запущен)
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
Set-Location $PSScriptRoot\..
& $py integrations/telegram_standalone.py
