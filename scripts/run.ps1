# AI Team Room — быстрый запуск (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$PyCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "python",
    "py"
)

$Py = $null
foreach ($c in $PyCandidates) {
    if ($c -eq "python" -or $c -eq "py") {
        try { & $c --version 2>$null | Out-Null; $Py = $c; break } catch {}
    } elseif (Test-Path $c) { $Py = $c; break }
}

if (-not $Py) {
    Write-Host "Python не найден. Установите: winget install Python.Python.3.12"
    exit 1
}

Write-Host "Using: $Py"
& $Py -m pip install -r requirements.txt -q
Write-Host "Starting AI Team Room at http://localhost:8000"
& $Py main.py
