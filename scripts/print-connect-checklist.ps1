# Выводит чеклист «где что подключить» в терминал
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Doc = Join-Path $Root "docs\WHERE_TO_CONNECT.md"

Write-Host ""
Write-Host "=== AI Team Room — куда что подключить ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. VPS (Timeweb/Hetzner)     -> порты 22, 80, 443"
Write-Host "2. DNS A-запись               -> room.ВАШ-ДОМЕН.ru -> IP VPS"
Write-Host "3. VPS .env                   -> cp .env.production.example .env"
Write-Host "4. Smart AIPI                 -> OPENAI_API_KEY в .env на VPS"
Write-Host "5. GitHub Secrets             -> VPS_HOST, VPS_USER, VPS_SSH_KEY"
Write-Host "6. Figma OAuth                -> Redirect: https://ДОМЕН/api/figma/callback"
Write-Host "7. Cursor API                 -> CURSOR_API_KEY в .env на VPS"
Write-Host ""
Write-Host "Полная инструкция:" -ForegroundColor Yellow
Write-Host "  $Doc"
Write-Host ""
Write-Host "Production шаблон .env:"
Write-Host "  $(Join-Path $Root '.env.production.example')"
Write-Host ""

if (Test-Path $Doc) {
    Write-Host "Открыть в редакторе: docs/WHERE_TO_CONNECT.md" -ForegroundColor Green
}
