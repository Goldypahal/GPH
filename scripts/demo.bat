@echo off
REM GIVIN Statewide Intelligence Platform Demo Launcher
echo ========================================================
echo   Launching GIVIN Demonstration Environment
echo ========================================================

python scripts\demo_seed.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Demo seeding failed.
    exit /b %ERRORLEVEL%
)

python scripts\run_demo.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Demo execution failed.
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Demonstration completed successfully.
