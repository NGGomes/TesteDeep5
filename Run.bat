@echo off
setlocal EnableDelayedExpansion
title SOC/CISO Dashboard Manager
break on

:MENU
cls
echo ========================================
echo    SOC/CISO Dashboard Manager
echo ========================================
echo.
echo   [1] Compile Dashboard (npm build)
echo   [2] Compile Extension (Chrome)
echo   [3] Run Full System
echo       SSE + Texer + FastAPI + Agent1 + Agent2
echo   [4] Run Agent 1 Only
echo       SSE + Texer + Agent1
echo   [5] Run Agent 2 Only
echo       SSE + Texer + Agent2
echo   [6] Clean Logs and Reports
echo   [7] Exit
echo.
echo ========================================
set "choice="
set /p choice="Enter your choice (1-7): "
if "!choice!"=="1" goto COMPILE_DASH
if "!choice!"=="2" goto COMPILE_EXT
if "!choice!"=="3" goto RUN_FULL
if "!choice!"=="4" goto RUN_AGENT1
if "!choice!"=="5" goto RUN_AGENT2
if "!choice!"=="6" goto CLEAN
if "!choice!"=="7" goto EXIT
echo Invalid choice.
timeout /t 2 >nul
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:COMPILE_DASH
cls
echo ========================================
echo    Compiling Dashboard Frontend
echo ========================================
echo.
where node >nul 2>nul || (echo [ERROR] Node.js not found. & pause & goto MENU)
where npm  >nul 2>nul || (echo [ERROR] npm not found.     & pause & goto MENU)
if not exist "soc-dashboard\frontend" (echo [ERROR] soc-dashboard\frontend not found. & pause & goto MENU)

pushd soc-dashboard\frontend
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install --silent --no-fund
    if !errorlevel! neq 0 (echo [ERROR] npm install failed! & popd & pause & goto MENU)
)
echo Building dashboard...
call npm run build --silent
set BUILD_ERR=!errorlevel!
popd
if !BUILD_ERR! neq 0 (echo [ERROR] Build failed! & pause & goto MENU)
echo.
echo ========================================
echo    Build completed successfully!
echo ========================================
echo Frontend: soc-dashboard\frontend\dist
echo.
set "pv="
set /p pv="Launch preview? (y/n): "
if /i "!pv!"=="y" (
    pushd soc-dashboard\frontend
    echo Starting preview on http://localhost:4173 ...
    echo Note: SSE server ^(port 5001^) and FastAPI ^(port 8000^) must be running
    echo       for full functionality. Start option [3] in another window.
    start "" "http://localhost:4173"
    call npm run preview
    popd
)
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:COMPILE_EXT
cls
echo ========================================
echo    Compiling Chrome Extension
echo ========================================
echo.
where node   >nul 2>nul || (echo [ERROR] Node.js not found. & pause & goto MENU)
where npm    >nul 2>nul || (echo [ERROR] npm not found.     & pause & goto MENU)
where python >nul 2>nul || (echo [ERROR] Python not found.  & pause & goto MENU)

set "EXT_DIR="
if exist "redshift-chrome-extension\package.json" set "EXT_DIR=redshift-chrome-extension"
if exist "extension\package.json"                 set "EXT_DIR=extension"
if "!EXT_DIR!"=="" (
    echo [ERROR] Extension directory not found.
    echo Expected: redshift-chrome-extension\  or  extension\
    pause & goto MENU
)

pushd !EXT_DIR!
if exist "dist" (
    echo Cleaning stale dist\...
    rmdir /s /q "dist"
)
if not exist "node_modules" (
    echo Installing extension dependencies...
    call npm install --silent --no-fund
    if !errorlevel! neq 0 (echo [ERROR] npm install failed! & popd & pause & goto MENU)
)
echo Building extension...
call npm run build --silent
set EXT_ERR=!errorlevel!
if !EXT_ERR! neq 0 (
    echo [WARN] Silent build failed, retrying with output...
    call npm run build
    set EXT_ERR=!errorlevel!
)
popd
if !EXT_ERR! neq 0 (echo [ERROR] Extension build failed! & pause & goto MENU)

echo.
echo ========================================
echo    Extension build completed!
echo ========================================
echo Output: !EXT_DIR!\dist
echo.

:: ── Start FastAPI backend for testing ───────────────────────────────────────
echo Starting FastAPI backend for extension testing...
echo   CVE analysis   ^→ http://localhost:8000/api/v1/analysis/cve
echo   SIEM analysis  ^→ http://localhost:8000/api/v1/analysis/siem
echo   Chat           ^→ http://localhost:8000/api/v1/analysis/chat
echo   Health         ^→ http://localhost:8000/health
echo.

:: Check if backend is already running
curl -s --max-time 1 http://localhost:8000/health >nul 2>nul
if !errorlevel! equ 0 (
    echo [INFO] FastAPI already running on port 8000.
) else (
    :: Backend lives at soc-dashboard\backend\, uvicorn module = app.main:app
    set "BACKEND_PY="
    if exist "soc-dashboard\backend\app\main.py" set "BACKEND_PY=soc-dashboard\backend"
    if exist "backend\app\main.py"               set "BACKEND_PY=backend"

    if "!BACKEND_PY!"=="" (
        echo [WARN] FastAPI not found. Extension CVE/SIEM/Chat analysis
        echo        will not work. Searched: soc-dashboard\backend\app\main.py
    ) else (
        echo Launching FastAPI from: !BACKEND_PY!\app\main.py
        start "FastAPI Backend :8000" cmd /k "cd /d !CD!\!BACKEND_PY! && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
        echo Waiting for FastAPI to be ready...
        set /a WAIT=0
    :WAIT_BACKEND
        timeout /t 1 >nul
        set /a WAIT+=1
        curl -s --max-time 1 http://localhost:8000/health >nul 2>nul
        if !errorlevel! equ 0 (
            echo [OK] FastAPI ready at http://localhost:8000
        ) else (
            if !WAIT! lss 15 goto WAIT_BACKEND
            echo [WARN] FastAPI did not respond in 15s - check the backend window.
        )
    )
)

echo.
echo To reload extension in Chrome:
echo   1. Opening chrome://extensions now...
echo   2. Click the reload ^(↺^) button on RedShift CVE Agent
echo      OR: Load unpacked ^→ select !EXT_DIR!\dist
echo.
echo [TIP] In the extension settings, confirm API URL = http://localhost:8000
echo.
start chrome "chrome://extensions"
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:RUN_FULL
cls
cmd /c "python launcher.py"
echo. & echo Full system stopped. & echo.
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:RUN_AGENT1
cls
echo ========================================
echo    Starting Agent 1 Only
echo ========================================
echo.
echo Services that will start:
echo   1. SSE Server         ^(port 5001^)
echo   2. Texer / LaTeX      ^(port 5002^)
echo   3. Agent 1            ^(alert processing^)
echo.
echo Note: FastAPI ^(port 8000^) and Agent 2 will NOT start.
echo       Extension CVE/SIEM analysis will not be available.
echo.
where python >nul 2>nul || (echo [ERROR] Python not found. & pause & goto MENU)
echo Press any key to start...
pause >nul
cmd /c "python launcher.py --agent1-only"
echo. & echo Agent 1 stopped. & echo.
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:RUN_AGENT2
cls
echo ========================================
echo    Starting Agent 2 Only
echo ========================================
echo.
echo Services that will start:
echo   1. SSE Server         ^(port 5001^)
echo   2. Texer / LaTeX      ^(port 5002^)
echo   3. Agent 2            ^(report generation^)
echo.
echo Note: FastAPI ^(port 8000^) and Agent 1 will NOT start.
echo       Alert processing will not run.
echo.
where python >nul 2>nul || (echo [ERROR] Python not found. & pause & goto MENU)
echo Press any key to start...
pause >nul
cmd /c "python launcher.py --agent2-only"
echo. & echo Agent 2 stopped. & echo.
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:CLEAN
cls
echo ========================================
echo    Cleaning Logs and Reports
echo ========================================
echo.
if exist "logs"    (rmdir /s /q "logs"    & echo Removed: logs)
if exist "reports" (rmdir /s /q "reports" & echo Removed: reports)
for /d /r . %%d in (__pycache__) do if exist "%%d" rmdir /s /q "%%d" 2>nul
del /q "agent1\classification_cache.json" 2>nul
echo. & echo Cleanup done. & echo.
pause
goto MENU

:: ═══════════════════════════════════════════════════════════════════════════
:EXIT
exit /b 0