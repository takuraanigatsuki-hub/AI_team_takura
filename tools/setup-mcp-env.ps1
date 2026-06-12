# MCP env helper for .cursor/mcp.json
# Run: powershell -ExecutionPolicy Bypass -File tools/setup-mcp-env.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$envFile = Join-Path $root ".env"

if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $root ".env.example") $envFile
    Write-Host "Created .env from .env.example - fill tokens and run again."
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

$sqliteDefault = Join-Path $root "data\ai_team.sqlite"
if (-not $envMap["SQLITE_DB_PATH"]) {
    Add-Content $envFile "`nSQLITE_DB_PATH=$sqliteDefault"
    $envMap["SQLITE_DB_PATH"] = $sqliteDefault
    Write-Host "Added SQLITE_DB_PATH=$sqliteDefault"
}

$mcpKeys = @(
    "GITHUB_TOKEN", "FIGMA_ACCESS_TOKEN", "NOTION_TOKEN", "LINEAR_API_KEY",
    "VERCEL_TOKEN", "CONTEXT7_API_KEY", "SENTRY_ACCESS_TOKEN",
    "SLACK_BOT_TOKEN", "SLACK_TEAM_ID", "DATABASE_URL", "SQLITE_DB_PATH",
    "JIRA_URL", "JIRA_TOKEN", "JIRA_EMAIL"
)

Write-Host ""
Write-Host "MCP env status (.env):"
foreach ($key in $mcpKeys) {
    if ($envMap[$key]) {
        Write-Host "  [ok] $key"
    } else {
        Write-Host "  [--] $key (optional)"
    }
}

Write-Host ""
Write-Host "OAuth on first use: linear, vercel, atlassian-jira, sentry"
Write-Host "Docker MCP needs: uv (pip install uv) or Docker Desktop"
Write-Host "Syncing .env values to Windows User environment (for Cursor MCP)..."
foreach ($key in $mcpKeys) {
    if ($envMap[$key]) {
        [Environment]::SetEnvironmentVariable($key, $envMap[$key], "User")
    }
}
Write-Host "Done. Restart Cursor fully (Settings -> Tools and MCP -> Refresh)."
