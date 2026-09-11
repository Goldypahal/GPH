@echo off
REM GIVIN Statewide Intelligence Platform Zero-to-Demo Launcher
echo ========================================================
echo   Launching GIVIN Zero-to-Demo Environment
echo ========================================================

python scripts\bootstrap_demo.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Demo bootstrap or execution failed with code %ERRORLEVEL%.
    exit /b %ERRORLEVEL%
)

echo [SUCCESS] Zero-to-Demo completed with exit code 0.

