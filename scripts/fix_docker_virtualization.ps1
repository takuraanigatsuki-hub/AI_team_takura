#Requires -RunAsAdministrator
<#
.SYNOPSIS
  Исправление Docker Desktop: WSL2 + виртуализация на Windows 11.
.NOTES
  Запуск: ПКМ → «Запуск от имени администратора»
  powershell -ExecutionPolicy Bypass -File scripts\fix_docker_virtualization.ps1
#>
$ErrorActionPreference = "Continue"

Write-Host "=== Docker / Virtualization fix ===" -ForegroundColor Cyan

Write-Host "`n[1] CPU virtualization (BIOS)" -ForegroundColor Yellow
try {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    $vtx = $cpu.VirtualizationFirmwareEnabled
    if ($null -eq $vtx) {
        Write-Host "  Cannot read firmware flag — check BIOS manually (Intel VT-x / AMD SVM = Enabled)"
    } elseif ($vtx) {
        Write-Host "  VirtualizationFirmwareEnabled: OK" -ForegroundColor Green
    } else {
        Write-Host "  VirtualizationFirmwareEnabled: OFF" -ForegroundColor Red
        Write-Host "  -> Reboot to BIOS (Del/F2/F12), enable Intel VT-x or AMD-V (SVM Mode)"
    }
} catch {
    Write-Host "  $($_.Exception.Message)"
}

Write-Host "`n[2] Windows features (WSL2 + Hyper-V platform)" -ForegroundColor Yellow
$features = @(
    "Microsoft-Windows-Subsystem-Linux",
    "VirtualMachinePlatform",
    "Microsoft-Hyper-V-All"
)
foreach ($f in $features) {
    $st = (Get-WindowsOptionalFeature -Online -FeatureName $f -ErrorAction SilentlyContinue).State
    if ($st -ne "Enabled") {
        Write-Host "  Enabling $f ..."
        Enable-WindowsOptionalFeature -Online -FeatureName $f -All -NoRestart | Out-Null
    } else {
        Write-Host "  $f : Enabled" -ForegroundColor Green
    }
}

Write-Host "`n[3] WSL2 kernel" -ForegroundColor Yellow
wsl --install --no-distribution 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  wsl --install needs reboot if features were just enabled" -ForegroundColor Yellow
}

Write-Host "`n[4] WSL default version = 2" -ForegroundColor Yellow
wsl --set-default-version 2 2>&1

Write-Host "`n[5] Hypervisor boot" -ForegroundColor Yellow
bcdedit /set hypervisorlaunchtype auto 2>&1

Write-Host "`n=== DONE ===" -ForegroundColor Green
Write-Host "1. REBOOT PC (обязательно после первой установки WSL)"
Write-Host "2. Open Docker Desktop → Settings → General → Use WSL 2 based engine"
Write-Host "3. Run: docker pull python:3.12-slim"
Write-Host ""
Write-Host "If BIOS VT-x is OFF — Docker will never start until you enable it in firmware."
Write-Host "Without Docker: AI Team sandbox still works in LOCAL mode (already configured)."
