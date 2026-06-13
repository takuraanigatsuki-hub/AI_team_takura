# AI Team Room — нативный desktop-клиент (WebView2 / .NET), без Python
# Требуется: .NET 8 SDK — winget install Microsoft.DotNet.SDK.8

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$Root\..\desktop-client\AITeamRoom.csproj") { $Root = Resolve-Path "$Root\.." }

Set-Location $Root
Write-Host "==> AI Team Room Native Desktop Build" -ForegroundColor Cyan

$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
if (-not $dotnet) {
    Write-Host "Installing .NET 8 SDK..." -ForegroundColor Yellow
    winget install Microsoft.DotNet.SDK.8 --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

New-Item -ItemType Directory -Force -Path "$Root\dist" | Out-Null

Write-Host "==> dotnet publish (native exe)..." -ForegroundColor Yellow
dotnet publish "$Root\desktop-client\AITeamRoom.csproj" -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o "$Root\dist\publish"

$Portable = Join-Path $Root "dist\publish\AI_Team_Room.exe"
if (-not (Test-Path $Portable)) {
    Write-Host "Build failed" -ForegroundColor Red
    exit 1
}
Copy-Item $Portable "$Root\dist\AI_Team_Room.exe" -Force
Write-Host "OK Portable: $Root\dist\AI_Team_Room.exe" -ForegroundColor Green

Write-Host "==> Installer wrapper..." -ForegroundColor Yellow
$py = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
if (Test-Path $py) {
    & $py -m pip install -q pyinstaller 2>$null
    & $py -m PyInstaller build-installer.spec --noconfirm
    if (Test-Path "$Root\dist\AI_Team_Room_Setup.exe") {
        Write-Host "OK Setup: $Root\dist\AI_Team_Room_Setup.exe" -ForegroundColor Green
    }
} else {
    Copy-Item "$Root\dist\AI_Team_Room.exe" "$Root\dist\AI_Team_Room_Setup.exe" -Force
    Write-Host "OK Setup (copy): dist\AI_Team_Room_Setup.exe" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Upload dist\ to VPS for /api/downloads/desktop/*" -ForegroundColor Cyan
