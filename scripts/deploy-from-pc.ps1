# Локально: push в GitHub → сервер обновится (если настроен GitHub Actions)
# Usage: .\scripts\deploy-from-pc.ps1 [-Message "описание изменений"]

param(
    [string]$Message = "deploy: sync from PC"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Git = "C:\Program Files\Git\bin\git.exe"

Set-Location $Root

if (-not (Test-Path $Git)) {
    Write-Host "Git не найден. Установите: winget install Git.Git"
    exit 1
}

& $Git status -sb
$dirty = & $Git status --porcelain
if (-not $dirty) {
    Write-Host "Нет изменений для push."
    exit 0
}

& $Git add -A
& $Git commit -m $Message
& $Git push origin main

Write-Host ""
Write-Host "OK — код на GitHub."
Write-Host "Если настроены VPS secrets → GitHub Actions обновит сервер автоматически."
Write-Host "Иначе на VPS: cd ~/AI_team_takura && bash scripts/deploy-vps.sh"
Write-Host "Документация: docs/DEPLOY.md"
