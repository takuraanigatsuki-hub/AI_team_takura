#Requires -Version 5.1
<#
.SYNOPSIS
  Настройка VFlex VPN для AI Team Room (Windows).
.USAGE
  powershell -ExecutionPolicy Bypass -File scripts/setup_vflex.ps1
  powershell -ExecutionPolicy Bypass -File scripts/setup_vflex.ps1 -SubscriptionUrl "https://vflex.ru/..."
#>
param(
    [string]$SubscriptionUrl = "https://vflex.ru/Jg1Jok4EngTf2Wo-",
    [string]$Proxy = "http://127.0.0.1:7890"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
$EnvFile = Join-Path $Root ".env"

function Set-EnvLine($key, $value) {
    $pattern = "^\s*$([regex]::Escape($key))\s*="
    $line = "$key=$value"
    if (-not (Test-Path $EnvFile)) { New-Item -ItemType File -Path $EnvFile | Out-Null }
    $content = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
    if ($content -match "(?m)^$([regex]::Escape($key))=") {
        $content = [regex]::Replace($content, "(?m)^$([regex]::Escape($key))=.*", $line)
    } else {
        if ($content -and -not $content.EndsWith("`n")) { $content += "`n" }
        $content += "$line`n"
    }
    Set-Content -Path $EnvFile -Value $content.TrimEnd() -Encoding UTF8
}

Write-Host "==> VFlex VPN setup" -ForegroundColor Cyan
Write-Host "    Subscription: $SubscriptionUrl"

Set-EnvLine "VFLEX_SUBSCRIPTION_URL" $SubscriptionUrl
Set-EnvLine "OUTBOUND_PROXY" $Proxy
Set-EnvLine "OUTBOUND_PROXY_MODE" "auto"

# Проверка локального прокси (NekoBox / Throne / Clash)
$port = 7890
if ($Proxy -match ':(\d+)$') { $port = [int]$Matches[1] }
$proxyUp = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect("127.0.0.1", $port)
    $proxyUp = $true
    $tcp.Close()
} catch { $proxyUp = $false }

if ($proxyUp) {
    Write-Host "    Local proxy 127.0.0.1:$port — ONLINE" -ForegroundColor Green
} else {
    Write-Host "    Local proxy 127.0.0.1:$port — offline (VPN client not running)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Install Throne or NekoBox (https://vflex.ru/... instructions)" -ForegroundColor White
    Write-Host "  2. Add subscription URL in the app" -ForegroundColor White
    Write-Host "  3. Connect to a server (mixed-port 7890 or enable TUN)" -ForegroundColor White
    Write-Host ""
    Write-Host "  Subscription (copy to VPN app):" -ForegroundColor Cyan
    Write-Host "  $SubscriptionUrl" -ForegroundColor Gray
}

if (Test-Path $Py) {
    Write-Host ""
    Write-Host "==> Connectivity check" -ForegroundColor Cyan
    Set-Location $Root
    & $Py scripts/check_connectivity.py
}

Write-Host ""
Write-Host "Done. Restart server: python main.py" -ForegroundColor Green
