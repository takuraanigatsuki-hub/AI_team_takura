#Requires -Version 5.1
# Ждёт готовности Docker Engine и скачивает образ sandbox
$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
if (-not (Test-Path $docker)) { exit 0 }
$desktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
if (Test-Path $desktop) { Start-Process $desktop -ErrorAction SilentlyContinue }
for ($i = 0; $i -lt 60; $i++) {
    & $docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        & $docker pull python:3.12-slim
        exit 0
    }
    Start-Sleep -Seconds 10
}
