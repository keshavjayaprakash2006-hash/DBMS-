@echo off
setlocal enabledelayedexpansion
title Semantic PYQ Analyzer - One-Click Launcher

echo =====================================================================
echo    SEMANTIC PYQ ANALYZER & STUDY HEATMAP - SYSTEM STARTUP
echo =====================================================================
echo.

:: 1. Check Docker Installation
echo [1/5] Checking Docker installation...
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    if exist "%ProgramFiles%\Docker\Docker\resources\bin\docker.exe" (
        set "PATH=%ProgramFiles%\Docker\Docker\resources\bin;%PATH%"
    ) else (
        echo [ERROR] Docker is not installed or not in your PATH.
        echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop/
        echo and ensure the Docker CLI is available.
        pause
        exit /b 1
    )
)
echo       Docker CLI detected.

:: 2. Check Docker Engine Daemon Status
echo.
echo [2/5] Checking Docker daemon status...
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       Docker Desktop is not currently running. Attempting to start it...
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
    ) else if exist "%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe" (
        start "" "%LocalAppData%\Programs\Docker\Docker\Docker Desktop.exe"
    ) else (
        echo [WARNING] Could not locate Docker Desktop executable automatically.
        echo Please open Docker Desktop manually from your Start Menu.
    )

    echo       Waiting for Docker engine to become ready (this may take 30-45s)...
    set /a attempts=0
    :wait_docker
    timeout /t 3 /nobreak >nul
    set /a attempts+=1
    docker info >nul 2>&1
    if %ERRORLEVEL% EQU 0 goto docker_ready
    if !attempts! GEQ 30 (
        echo.
        echo [ERROR] Timed out waiting for Docker engine.
        echo Please open Docker Desktop, ensure the engine is running, and re-run this script.
        pause
        exit /b 1
    )
    <nul set /p=.
    goto wait_docker

    :docker_ready
    echo.
)
echo       Docker engine is active and ready.

:: 3. Check Ollama & AI Model
echo.
echo [3/5] Checking Ollama AI Assistant service...
curl -s -m 3 http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       [NOTICE] Ollama does not appear to be running on http://localhost:11434
    echo       Attempting to start Ollama in the background...
    where ollama >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        start /b ollama serve >nul 2>&1
        timeout /t 3 /nobreak >nul
    )
    curl -s -m 3 http://localhost:11434/api/tags >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo       [NOTE] Ollama could not be started automatically.
        echo       The main application (Notes, PYQs, Heatmap, Semantic Search)
        echo       will work completely offline. To use AI Chat, start Ollama manually:
        echo       Open a new terminal and run: ollama serve
    ) else (
        echo       Ollama is now online.
    )
) else (
    echo       Ollama is running on http://localhost:11434.
)

:: 4. Start Docker Containers
echo.
echo [4/5] Launching application containers (PostgreSQL + pgvector, FastAPI, React)...
docker compose up -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Docker containers.
    echo Check the error message above or run: docker compose logs
    pause
    exit /b 1
)

:: 5. Wait for Services to Become Healthy
echo.
echo [5/5] Waiting for backend API and PostgreSQL to become healthy...
set /a backend_attempts=0
:wait_backend
timeout /t 3 /nobreak >nul
set /a backend_attempts+=1
curl -s -f http://localhost:8000/health >nul 2>&1
if %ERRORLEVEL% EQU 0 goto backend_ready
if !backend_attempts! GEQ 40 (
    echo.
    echo [WARNING] Backend is taking longer than expected to report healthy.
    echo Checking container logs...
    docker compose logs --tail=15 backend
    goto open_browser
)
<nul set /p=.
goto wait_backend

:backend_ready
echo.
echo       Backend API and PostgreSQL database are healthy!

:open_browser
echo.
echo =====================================================================
echo    APPLICATION STARTED SUCCESSFULLY!
echo =====================================================================
echo.
echo    * Frontend UI:         http://localhost:3000
echo    * Backend REST API:    http://localhost:8000
echo    * Interactive API Docs: http://localhost:8000/docs
echo    * PostgreSQL Database: localhost:5432 (database: pyq_analyzer)
echo    * Ollama Local LLM:    http://localhost:11434
echo.
echo Opening the frontend in your default web browser...
start http://localhost:3000

echo.
echo Tip: To stop the project safely without deleting your database or notes,
echo      double-click stop-dbms.bat
echo.
pause
