# Подготовка переменных окружения для MCP (.cursor/mcp.json)
# Запуск: .\tools\setup-mcp-env.ps1
# Затем перезапустите Cursor (Settings → MCP → Reload)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root ".env"

if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "Создан .env из .env.example — заполните токены и запустите снова." -ForegroundColor Yellow
    exit 1
}

function Read-DotEnv($path) {
    $map = @{}
    Get-Content $path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
        if ($k) { $map[$k] = $v }
    }
    return $map
}

$envMap = Read-DotEnv $envFile

$defaults = @{
    SQLITE_DB_PATH = (Join-Path $root "data\ai_team.sqlite")
}

foreach ($key in $defaults.Keys) {
    if (-not $envMap[$key]) {
        $envMap[$key] = $defaults[$key]
        Add-Content $envFile "`n$key=$($defaults[$key])"
        Write-Host "Добавлено в .env: $key=$($defaults[$key])"
    }
}

$mcpKeys = @(
    "GITHUB_TOKEN", "FIGMA_ACCESS_TOKEN", "NOTION_TOKEN", "LINEAR_API_KEY",
    "VERCEL_TOKEN", "CONTEXT7_API_KEY", "SENTRY_ACCESS_TOKEN",
    "SLACK_BOT_TOKEN", "SLACK_TEAM_ID", "DATABASE_URL", "SQLITE_DB_PATH",
    "JIRA_URL", "JIRA_TOKEN", "JIRA_EMAIL"
)

Write-Host "`nMCP — статус переменных в .env:" -ForegroundColor Cyan
foreach ($key in $mcpKeys) {
    $val = $envMap[$key]
    if ($val) {
        Write-Host "  [OK]  $key"
    } else {
        Write-Host "  [--]  $key (не задан — сервер может быть жёлтым в Cursor)"
    }
}

Write-Host "`nOAuth при первом использовании: linear, vercel, atlassian-jira, sentry" -ForegroundColor Gray
Write-Host "Docker MCP требует: uv (pip install uv) или Docker Desktop" -ForegroundColor Gray
Write-Host "Перезагрузите MCP: Cursor → Settings → Tools & MCP → Refresh" -ForegroundColor Green
