@echo off
REM ========================================
REM OpenClaw Docker Startup Script
REM ========================================

set CONFIG_DIR=D:\docker_env\openclaw
set IMAGE=ghcr.io/openclaw/openclaw:latest
set CONTAINER_NAME=openclaw-gateway
set PORT=18789

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM --- Onboard if no config ---
if not exist "%CONFIG_DIR%\.env" (
    echo [INFO] No config found. Running onboard...
    echo [INFO] Follow the prompts to set up API keys.
    docker run -it --rm -v %CONFIG_DIR%:/root/.openclaw %IMAGE% openclaw onboard
    if errorlevel 1 (
        echo [ERROR] Onboard failed. Check the error above.
        pause
        exit /b 1
    )
    echo [INFO] Onboard complete.
)

REM --- Check if container exists ---
docker inspect --format="{{.Name}}" %CONTAINER_NAME% >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Container exists, restarting...
    docker restart %CONTAINER_NAME%
) else (
    echo [INFO] Starting OpenClaw Gateway...
    docker run -d --name %CONTAINER_NAME% -p %PORT%:%PORT% -v %CONFIG_DIR%:/root/.openclaw %IMAGE%
)

if %errorlevel%==0 (
    echo [INFO] OpenClaw Gateway started: http://localhost:%PORT%
    echo [INFO] View logs:  docker logs -f %CONTAINER_NAME%
    echo [INFO] Run CLI:    docker exec -it %CONTAINER_NAME% openclaw [command]
) else (
    echo [ERROR] Startup failed. Check the error above.
)

pause