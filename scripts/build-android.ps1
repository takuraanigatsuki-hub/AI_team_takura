# AI Team Room — сборка Android APK (WebView companion)
# Требуется: JDK 17+, Android SDK (cmdline-tools)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path "$Root\..\android-companion\android\settings.gradle") { $Root = Resolve-Path "$Root\.." }

$Dist = Join-Path $Root "dist"
$SdkRoot = if ($env:ANDROID_HOME) { $env:ANDROID_HOME } elseif ($env:ANDROID_SDK_ROOT) { $env:ANDROID_SDK_ROOT } else { Join-Path $Root ".android-sdk" }
$AndroidDir = Join-Path $Root "android-companion\android"

New-Item -ItemType Directory -Force -Path $Dist | Out-Null
New-Item -ItemType Directory -Force -Path $SdkRoot | Out-Null

function Ensure-Java {
    $glob = Get-ChildItem "C:\Program Files\Microsoft\jdk-17*\bin\java.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($glob) {
        $env:JAVA_HOME = Split-Path (Split-Path $glob.FullName)
        $env:Path = "$($glob.DirectoryName);" + $env:Path
        Write-Host "Java: $($glob.FullName)" -ForegroundColor Gray
        return
    }
    $javaCmd = Get-Command java -ErrorAction SilentlyContinue
    if ($javaCmd -and (Test-Path $javaCmd.Source)) {
        $env:JAVA_HOME = Split-Path (Split-Path $javaCmd.Source)
        Write-Host "Java: $($javaCmd.Source)" -ForegroundColor Gray
        return
    }
    Write-Host "Installing Microsoft OpenJDK 17..." -ForegroundColor Yellow
    winget install Microsoft.OpenJDK.17 --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
    Ensure-Java
}

function Ensure-AndroidSdk {
    $cmdline = Join-Path $SdkRoot "cmdline-tools\latest\bin\sdkmanager.bat"
    if (-not (Test-Path $cmdline)) {
        Write-Host "Downloading Android commandline-tools..." -ForegroundColor Yellow
        $zip = Join-Path $env:TEMP "cmdline-tools.zip"
        $url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
        Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
        $extract = Join-Path $env:TEMP "android-cmdline"
        if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $extract -Force
        $dest = Join-Path $SdkRoot "cmdline-tools\latest"
        New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
        Move-Item (Join-Path $extract "cmdline-tools") $dest -Force
    }
    $env:ANDROID_HOME = $SdkRoot
    $env:ANDROID_SDK_ROOT = $SdkRoot
    Write-Host "Installing SDK packages (platform 34, build-tools)..." -ForegroundColor Yellow
    $yes = "y`n" * 20
    $yes | & $cmdline --sdk_root=$SdkRoot "platform-tools" "platforms;android-34" "build-tools;34.0.0" 2>&1 | Out-Null
}

function Ensure-GradleWrapper {
    $jar = Join-Path $AndroidDir "gradle\wrapper\gradle-wrapper.jar"
    if ((Test-Path $jar) -and ((Get-Item $jar).Length -lt 10000)) {
        Remove-Item $jar -Force -ErrorAction SilentlyContinue
    }
    if ((Test-Path $jar) -and ((Get-Item $jar).Length -gt 30000)) { return }
    Write-Host "Bootstrapping Gradle 8.7..." -ForegroundColor Yellow
    $gradleZip = Join-Path $env:TEMP "gradle-8.7-bin.zip"
    if (-not (Test-Path $gradleZip)) {
        Invoke-WebRequest -Uri "https://services.gradle.org/distributions/gradle-8.7-bin.zip" -OutFile $gradleZip -UseBasicParsing
    }
    $gradleHome = Join-Path $env:TEMP "gradle-8.7"
    if (-not (Test-Path "$gradleHome\bin\gradle.bat")) {
        Expand-Archive -Path $gradleZip -DestinationPath $env:TEMP -Force
    }
    Push-Location $AndroidDir
    & "$gradleHome\bin\gradle.bat" wrapper --gradle-version 8.7 2>&1 | Out-Host
    Pop-Location
}

function Test-GradleWrapperReady {
    $wrapper = Join-Path $AndroidDir "gradlew.bat"
    $jar = Join-Path $AndroidDir "gradle\wrapper\gradle-wrapper.jar"
    return (Test-Path $wrapper) -and (Test-Path $jar) -and ((Get-Item $jar).Length -gt 30000)
}

function Invoke-GradleBuild {
    param([string]$Task)
    if (Test-GradleWrapperReady) {
        Push-Location $AndroidDir
        & (Join-Path $AndroidDir "gradlew.bat") $Task --no-daemon 2>&1 | Out-Host
        $code = $LASTEXITCODE
        Pop-Location
        if ($null -eq $code) { $code = 1 }
        if ($code -eq 0) { return 0 }
        Write-Host "gradlew failed (exit $code), bootstrapping Gradle 8.7..." -ForegroundColor Yellow
    }
    Ensure-GradleWrapper
    $gradleHome = Join-Path $env:TEMP "gradle-8.7"
    if (-not (Test-Path "$gradleHome\bin\gradle.bat")) {
        Write-Host "Gradle 8.7 not found after bootstrap" -ForegroundColor Red
        return 1
    }
    Push-Location $AndroidDir
       & "$gradleHome\bin\gradle.bat" $Task --no-daemon 2>&1 | Out-Host
    $code = $LASTEXITCODE
    Pop-Location
    if ($null -eq $code) { $code = 1 }
    return [int]$code
}

Write-Host "==> AI Team Room Android APK Build" -ForegroundColor Cyan
Ensure-Java
Ensure-AndroidSdk
Ensure-GradleWrapper

$env:ANDROID_HOME = $SdkRoot
$env:ANDROID_SDK_ROOT = $SdkRoot
$env:JAVA_HOME = $env:JAVA_HOME  # winget usually sets this

Push-Location $AndroidDir
Write-Host "==> gradle assembleRelease..." -ForegroundColor Yellow
Pop-Location
[int]$code = Invoke-GradleBuild "assembleRelease"
if ($code -ne 0) {
    Write-Host "Release failed, trying assembleDebug..." -ForegroundColor Yellow
    [int]$code = Invoke-GradleBuild "assembleDebug"
    if ($code -ne 0) { exit $code }
    $apk = Get-ChildItem -Path (Join-Path $AndroidDir "app\build\outputs\apk\debug") -Filter "*.apk" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
} else {
    $apk = Get-ChildItem -Path (Join-Path $AndroidDir "app\build\outputs\apk\release") -Filter "*.apk" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
}

if (-not $apk) {
    Write-Host "APK not found after build" -ForegroundColor Red
    exit 1
}

$out = Join-Path $Dist "AI_Team_Room.apk"
Copy-Item $apk.FullName $out -Force
$mb = [math]::Round((Get-Item $out).Length / 1MB, 2)
Write-Host "OK APK: $out ($mb MB)" -ForegroundColor Green
Write-Host "Upload to VPS dist/ for /api/downloads/android/apk" -ForegroundColor Cyan
