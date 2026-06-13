#Requires -Version 5.1
<#
.SYNOPSIS
  Полная автонастройка AI Team Room (Smart AIPI, RAG, Playwright, зависимости).
.USAGE
  powershell -ExecutionPolicy Bypass -File scripts/setup_all.ps1
#>
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"

if (-not (Test-Path $Py)) {
    Write-Host "Python 3.12 not found at $Py" -ForegroundColor Red
    exit 1
}

Set-Location $Root
Write-Host "==> pip install requirements" -ForegroundColor Cyan
& $Py -m pip install -r requirements.txt -q

Write-Host "==> Playwright Chromium" -ForegroundColor Cyan
& $Py -m playwright install chromium

Write-Host "==> RAG knowledge packs" -ForegroundColor Cyan
& $Py scripts/ingest_knowledge_packs.py 2>$null

Write-Host "==> RAG URL docs + corpora" -ForegroundColor Cyan
& $Py scripts/ingest_doc_urls.py 2>$null
& $Py scripts/ingest_corpora.py 2>$null

Write-Host "==> RAG embeddings (Smart AIPI)" -ForegroundColor Cyan
& $Py -c "import asyncio, config; from integrations.rag.embed_index import embed_all_chunks; print(asyncio.run(embed_all_chunks(force=True)))"

Write-Host "==> Docker (optional)" -ForegroundColor Cyan
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Host "    Docker not found. Trying winget install Docker Desktop..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements 2>$null
        Write-Host "    If installed, restart PC and enable WSL2, then: docker pull python:3.12-slim" -ForegroundColor Yellow
    } else {
        Write-Host "    winget unavailable — sandbox uses local Python fallback" -ForegroundColor Yellow
    }
} else {
    docker pull python:3.12-slim 2>$null
    Write-Host "    Docker OK" -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete. Start server:" -ForegroundColor Green
Write-Host "  cd $Root"
Write-Host "  & `"$Py`" main.py"
