# Upload project to VPS and hot-reload Docker (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$Root\..\app.py") { $Root = Resolve-Path "$Root\.." }

$Key = "$env:USERPROFILE\.ssh\ai_team_regru"
$Host_ = "root@80.78.245.66"
$Remote = "/root/AI_team_takura"
$Scp = @("scp", "-i", $Key, "-o", "StrictHostKeyChecking=accept-new")

Write-Host "==> Upload to VPS $Host_" -ForegroundColor Cyan

$Dirs = @("static", "room", "integrations", "agents", "scripts", "android-companion")
$Files = @("app.py", "config.py", "knowledge_store.py", "README.md")

foreach ($d in $Dirs) {
    $src = Join-Path $Root $d
    if (Test-Path $src) {
        Write-Host "  -> $d/" -ForegroundColor Gray
        & $Scp -r $src "${Host_}:${Remote}/"
    }
}
foreach ($f in $Files) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        & $Scp $src "${Host_}:${Remote}/"
    }
}

New-Item -ItemType Directory -Force -Path "$Root\dist" | Out-Null
foreach ($bin in @("AI_Team_Room_Setup.exe", "AI_Team_Room.exe", "AI_Team_Room.apk")) {
    $p = Join-Path $Root "dist\$bin"
    if (Test-Path $p) {
        Write-Host "  -> dist/$bin" -ForegroundColor Gray
        ssh -i $Key $Host_ "mkdir -p $Remote/dist"
        & $Scp $p "${Host_}:${Remote}/dist/"
    }
}

& $Scp (Join-Path $Root "scripts\deploy-full-vps.sh") "${Host_}:${Remote}/scripts/"
ssh -i $Key $Host_ "chmod +x $Remote/scripts/deploy-full-vps.sh && bash $Remote/scripts/deploy-full-vps.sh"

Write-Host "OK VPS deploy" -ForegroundColor Green
