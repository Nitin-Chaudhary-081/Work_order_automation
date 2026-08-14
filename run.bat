@echo off
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" watcher.py
) else (
    python watcher.py
)

if errorlevel 1 (
    echo.
    echo The watcher stopped with an error. See automation.log for details.
    pause
)
