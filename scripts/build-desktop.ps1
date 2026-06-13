# AI Team Room — сборка десктоп-приложения для Windows
# Требуется: Python 3.10+, pip install pywebview pyinstaller
# Опционально: Inno Setup 6 для установщика

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$Root\..\desktop.py") { $Root = Resolve-Path "$Root\.." }

Set-Location $Root
Write-Host "==> AI Team Room Desktop build" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found in PATH" -ForegroundColor Red
    exit 1
}

python -m pip install -q pywebview pyinstaller 2>$null

New-Item -ItemType Directory -Force -Path "$Root\dist" | Out-Null

Write-Host "==> PyInstaller (portable exe)..." -ForegroundColor Yellow
python -m PyInstaller build-client.spec --noconfirm
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Portable = Join-Path $Root "dist\AI_Team_Room.exe"
if (-not (Test-Path $Portable)) {
    Write-Host "Build failed: AI_Team_Room.exe not found" -ForegroundColor Red
    exit 1
}
Write-Host "OK Portable: $Portable" -ForegroundColor Green

$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $Iscc)) {
    $Iscc = "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
}

if (Test-Path $Iscc) {
    Write-Host "==> Inno Setup installer..." -ForegroundColor Yellow
    & $Iscc "$Root\installer\AI_Team_Room.iss"
    if ($LASTEXITCODE -eq 0) {
        Write-Host "OK Installer: $Root\dist\AI_Team_Room_Setup.exe" -ForegroundColor Green
    }
} else {
    Write-Host "Inno Setup not found — skip installer (portable exe ready)" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "Upload dist\AI_Team_Room_Setup.exe to server for /download page" -ForegroundColor Cyan
