@echo off
REM ========================================
REM OpenClaw Docker Startup Script
REM ========================================

set CONFIG_DIR=D:\docker_env\openclaw
set IMAGE=ghcr.io/openclaw/openclaw:latest
set CONTAINER_NAME=openclaw-gateway
set PORT=18789
REM 网关鉴权 token（Control UI 通过 URL fragment ?token=... 认为）
if "%OPENCLAW_GATEWAY_TOKEN%"=="" set OPENCLAW_GATEWAY_TOKEN=5d127220bc8ff1d7175b0b341556849d6ee20b9f287cbaa707797cb614c782f5

if not exist "%CONFIG_DIR%" mkdir "%CONFIG_DIR%"

REM --- Sync openclaw.json from workspace into mounted config dir ---
if exist "%~dp0openclaw.json" copy /Y "%~dp0openclaw.json" "%CONFIG_DIR%\openclaw.json" >nul

REM --- Onboard if no config ---
if not exist "%CONFIG_DIR%\.env" (
    echo [INFO] No config found. Running onboard...
    echo [INFO] Follow the prompts to set up API keys.
    docker run -it --rm -v %CONFIG_DIR%:/home/node/.openclaw --entrypoint tini %IMAGE% -s -- node openclaw.mjs onboard
    if errorlevel 1 (
        echo [ERROR] Onboard failed. Check the error above.
        pause
        exit /b 1
    )
    echo [INFO] Onboard complete.
)

REM --- Remove stale container if it exists (port/route mismatches) ---
docker inspect --format="{{.Name}}" %CONTAINER_NAME% >nul 2>&1
if %errorlevel%==0 (
    echo [INFO] Existing container found. Removing and recreating...
    docker rm -f %CONTAINER_NAME% >nul
)

echo [INFO] Starting OpenClaw Gateway...
docker run -d --name %CONTAINER_NAME% -p %PORT%:%PORT% ^
  -v %CONFIG_DIR%:/home/node/.openclaw ^
  -v %CONFIG_DIR%\.env:/home/node/.openclaw/.env ^
  --env-file %CONFIG_DIR%\.env ^
  -e OPENCLAW_GATEWAY_TOKEN=%OPENCLAW_GATEWAY_TOKEN% ^
  --entrypoint tini %IMAGE% -s -- node openclaw.mjs gateway run --port %PORT% --token %OPENCLAW_GATEWAY_TOKEN% --allow-unconfigured

if %errorlevel%==0 (
    echo [INFO] OpenClaw Gateway started.
    echo [INFO] Dashboard: http://localhost:%PORT%/#token=%OPENCLAW_GATEWAY_TOKEN%
    echo [INFO] Health:    http://localhost:%PORT%/health
    echo [INFO] View logs: docker logs -f %CONTAINER_NAME%
    echo [INFO] Run CLI:   docker exec -it %CONTAINER_NAME% openclaw [command]
) else (
    echo [ERROR] Startup failed. Check the error above.
)

pause