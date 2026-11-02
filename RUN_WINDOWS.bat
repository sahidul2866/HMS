@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title HMS - Hospital Management System

echo ============================================================
echo   Hospital Management System (HMS) - Windows Launcher
echo ============================================================
echo.

rem 1. Check Node.js
where node >nul 2>&1 || (
    echo [ERROR] Node.js was not found on PATH. Please install Node.js LTS.
    pause
    exit /b 1
)

rem 2. Check Python
where python >nul 2>&1 || (
    where py >nul 2>&1 || (
        echo [ERROR] Python 3 was not found on PATH. Please install Python 3.12+.
        pause
        exit /b 1
    )
)

rem 3. Ensure backend/.env exists
if not exist "backend\.env" (
    if exist "backend\.env.example" (
        echo [WARNING] backend\.env was not found. Creating from .env.example...
        copy "backend\.env.example" "backend\.env" >nul
        echo [NOTICE] Please review backend\.env and configure DATABASE_URL.
    ) else (
        echo [ERROR] Missing backend\.env configuration.
        pause
        exit /b 1
    )
)

rem 4. Auto-launch browser when the frontend is ready (background watcher)
start "" powershell -NoProfile -WindowStyle Hidden -Command ^
  "$url='http://localhost:4200'; for($i=0;$i -lt 90;$i++){ try { $r=Invoke-WebRequest -UseBasicParsing $url -TimeoutSec 2; if($r.StatusCode -eq 200){Start-Process $url; exit 0} } catch {}; Start-Sleep -Seconds 1 }; exit 0"

set "FLAGS=-SkipPacs -NoViewer"
if /I "%~1"=="--full" set "FLAGS="
if /I "%~1"=="--pacs" set "FLAGS="

echo Starting HMS application...
echo   - Frontend: http://localhost:4200
echo   - Backend:  http://127.0.0.1:8000
echo   - Swagger:  http://127.0.0.1:8000/docs
echo.
echo Keep this window open while using the application.
echo (Press Ctrl+C to stop)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev-windows.ps1" %FLAGS%

if errorlevel 1 (
    echo.
    echo [ERROR] Application stopped or encountered an error.
    pause
    exit /b 1
)

exit /b 0

