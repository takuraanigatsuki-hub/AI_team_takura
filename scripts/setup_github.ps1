# Создание репозитория на GitHub и первый push
# Требуется: GitHub CLI (gh auth login) или создайте repo вручную на github.com

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/takuraanigatsuki-hub/AI_team_takura"
$RepoName = "AI_team_takura"
$Owner = "takuraanigatsuki-hub"
$Git = "C:\Program Files\Git\bin\git.exe"

Set-Location $PSScriptRoot\..

if (-not (Test-Path $Git)) {
    Write-Host "Git не найден. Установите: winget install Git.Git"
    exit 1
}

if (-not (Test-Path ".git")) {
    & $Git init
    & $Git branch -M main
}

$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    $auth = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Создаю репозиторий $RepoName на GitHub..."
        gh repo create $RepoName --public --source=. --remote=origin --push 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Repo может уже существовать — пробую push..."
            & $Git remote remove origin 2>$null
            & $Git remote add origin "$RepoUrl.git"
            & $Git push -u origin main
        }
        exit 0
    }
    Write-Host "Выполните: gh auth login"
    exit 1
}

Write-Host @"
GitHub CLI (gh) не установлен.

Вариант A — вручную:
  1. Откройте https://github.com/new
  2. Имя: $RepoName
  3. Без README (репо пустой)
  4. Затем в этой папке:
     git remote add origin $RepoUrl.git
     git push -u origin main

Вариант B — установите gh:
  winget install GitHub.cli
  gh auth login
  .\scripts\setup_github.ps1
"@
