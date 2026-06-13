# Авто-установка AI Team Room на REG.RU VPS
# Usage:
#   .\scripts\setup-reg-ru-remote.ps1 -VpsHost 185.x.x.x
#   .\scripts\setup-reg-ru-remote.ps1 -VpsHost 185.x.x.x -AppDomain room.site.ru -UseProd

param(
    [Parameter(Mandatory = $true)]
    [string]$VpsHost,
    [string]$VpsUser = "root",
    [string]$AppDomain = "localhost",
    [string]$OwnerEmail = "",
    [string]$OwnerPassword = "",
    [string]$OwnerName = "Owner",
    [switch]$UseProd
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Key = "$env:USERPROFILE\.ssh\ai_team_regru"
$Ssh = "C:\Program Files\Git\usr\bin\ssh.exe"
$Scp = "C:\Program Files\Git\usr\bin\scp.exe"

if (-not (Test-Path $Key)) {
    Write-Host "SSH key not found: $Key"
    Write-Host "Run setup again after key generation."
    exit 1
}

function Read-DotEnv([string]$Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $i = $line.IndexOf("=")
        if ($i -lt 1) { return }
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim()
        $map[$k] = $v
    }
    return $map
}

$localEnv = Read-DotEnv (Join-Path $Root ".env")
$pgPass = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 24 | ForEach-Object { [char]$_ })

$prodLines = @(
    "APP_DOMAIN=$AppDomain",
    "OPENAI_API_KEY=$($localEnv['OPENAI_API_KEY'])",
    "OPENAI_BASE_URL=$($localEnv['OPENAI_BASE_URL'])",
    "LLM_MODEL=$($localEnv['LLM_MODEL'])",
    "LLM_ROUTER_MODEL=$($localEnv['LLM_ROUTER_MODEL'])",
    "EMBEDDING_MODEL=$($localEnv['EMBEDDING_MODEL'])",
    "POSTGRES_USER=aiteam",
    "POSTGRES_PASSWORD=$pgPass",
    "POSTGRES_DB=aiteam",
    "DATABASE_URL=postgresql://aiteam:${pgPass}@postgres:5432/aiteam",
    "SQLITE_DB_PATH=data/ai_team.sqlite",
    "CURSOR_API_KEY=$($localEnv['CURSOR_API_KEY'])",
    "CURSOR_REPO_URL=$($localEnv['CURSOR_REPO_URL'])",
    "GITHUB_TOKEN=$($localEnv['GITHUB_TOKEN'])",
    "FIGMA_CLIENT_ID=$($localEnv['FIGMA_CLIENT_ID'])",
    "FIGMA_CLIENT_SECRET=$($localEnv['FIGMA_CLIENT_SECRET'])",
    "FIGMA_ACCESS_TOKEN=$($localEnv['FIGMA_ACCESS_TOKEN'])",
    "TELEGRAM_BOT_TOKEN=$($localEnv['TELEGRAM_BOT_TOKEN'])",
    "TELEGRAM_CHAT_ID=$($localEnv['TELEGRAM_CHAT_ID'])",
    "TELEGRAM_POLLING=$($localEnv['TELEGRAM_POLLING'])",
    "OUTBOUND_PROXY_MODE=off",
    "OUTBOUND_PROXY="
)

if ($AppDomain -ne "localhost") {
    $prodLines += "FIGMA_REDIRECT_URI=https://${AppDomain}/api/figma/callback"
} else {
    $prodLines += "FIGMA_REDIRECT_URI=http://${VpsHost}:8000/api/figma/callback"
}

$tmpEnv = Join-Path $env:TEMP "ai-team-prod.env"
$prodLines | Set-Content -Path $tmpEnv -Encoding UTF8

Write-Host "==> Test SSH to ${VpsUser}@${VpsHost}" -ForegroundColor Cyan
& $Ssh -i $Key -o StrictHostKeyChecking=accept-new -o BatchMode=yes "${VpsUser}@${VpsHost}" "echo SSH_OK"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "SSH failed. Add this public key in REG.RU panel (VPS -> SSH keys):" -ForegroundColor Yellow
    Get-Content "$Key.pub"
    Write-Host ""
    Write-Host "Then re-run: .\scripts\setup-reg-ru-remote.ps1 -VpsHost $VpsHost"
    exit 1
}

Write-Host "==> Upload .env and bootstrap script"
& $Scp -i $Key -o StrictHostKeyChecking=accept-new $tmpEnv "${VpsUser}@${VpsHost}:/tmp/ai-team.env"
& $Scp -i $Key -o StrictHostKeyChecking=accept-new (Join-Path $Root "scripts\reg-ru-bootstrap.sh") "${VpsUser}@${VpsHost}:/tmp/reg-ru-bootstrap.sh"

$useProdFlag = if ($UseProd) { "1" } else { "0" }
$ownerEnv = ""
if ($OwnerEmail -and $OwnerPassword) {
    $ownerEnv = "OWNER_EMAIL='$OwnerEmail' OWNER_PASSWORD='$OwnerPassword' OWNER_NAME='$OwnerName'"
}

Write-Host "==> Run bootstrap (5-10 min)"
$remoteCmd = "chmod +x /tmp/reg-ru-bootstrap.sh && USE_PROD=$useProdFlag $ownerEnv bash /tmp/reg-ru-bootstrap.sh"
& $Ssh -i $Key -o StrictHostKeyChecking=accept-new "${VpsUser}@${VpsHost}" $remoteCmd

Remove-Item $tmpEnv -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Ready ===" -ForegroundColor Green
if ($AppDomain -ne "localhost") {
    Write-Host "  https://${AppDomain}/app"
} else {
    Write-Host "  http://${VpsHost}:8000/app"
}
