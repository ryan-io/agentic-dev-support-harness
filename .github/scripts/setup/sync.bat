@echo off
cd /d "%~dp0..\..\..\"
where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found on PATH. Install Python 3 and retry.
    pause
    exit /b 1
)
python .github\scripts\sync-claude-rules.py
pause
