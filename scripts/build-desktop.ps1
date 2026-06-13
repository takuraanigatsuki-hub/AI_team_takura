# AI Team Room — нативный desktop-клиент + установщик (.NET 8 / WebView2)
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

Write-Host "==> dotnet publish client..." -ForegroundColor Yellow
dotnet publish "$Root\desktop-client\AITeamRoom.csproj" -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o "$Root\dist\publish-client"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Portable = Join-Path $Root "dist\publish-client\AI_Team_Room.exe"
if (-not (Test-Path $Portable)) {
    Write-Host "Client build failed" -ForegroundColor Red
    exit 1
}
Copy-Item $Portable "$Root\dist\AI_Team_Room.exe" -Force
Write-Host "OK Portable: $Root\dist\AI_Team_Room.exe" -ForegroundColor Green

Write-Host "==> dotnet publish updater..." -ForegroundColor Yellow
dotnet publish "$Root\desktop-updater\AITeamRoom.Updater.csproj" -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o "$Root\dist\publish-updater"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item "$Root\dist\publish-updater\AI_Team_Room_Updater.exe" "$Root\dist\AI_Team_Room_Updater.exe" -Force

Write-Host "==> dotnet publish uninstaller..." -ForegroundColor Yellow
dotnet publish "$Root\desktop-uninstaller\AITeamRoom.Uninstaller.csproj" -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o "$Root\dist\publish-uninstall"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Copy-Item "$Root\dist\publish-uninstall\AI_Team_Room_Uninstall.exe" "$Root\dist\AI_Team_Room_Uninstall.exe" -Force

Write-Host "==> dotnet publish installer..." -ForegroundColor Yellow
dotnet publish "$Root\desktop-installer\AITeamRoom.Installer.csproj" -c Release -r win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o "$Root\dist\publish-setup"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Setup = Join-Path $Root "dist\publish-setup\AI_Team_Room_Setup.exe"
if (-not (Test-Path $Setup)) {
    Write-Host "Installer build failed" -ForegroundColor Red
    exit 1
}
Copy-Item $Setup "$Root\dist\AI_Team_Room_Setup.exe" -Force
$setupSize = (Get-Item "$Root\dist\AI_Team_Room_Setup.exe").Length
if ($setupSize -lt 1MB) {
    Write-Host "Installer output suspiciously small ($setupSize bytes)" -ForegroundColor Red
    exit 1
}
Write-Host "OK Setup: $Root\dist\AI_Team_Room_Setup.exe" -ForegroundColor Green

Write-Host ""
Write-Host "Upload dist\ to VPS for /api/downloads/desktop/*" -ForegroundColor Cyan
