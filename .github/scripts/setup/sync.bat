@echo off
cd /d "%~dp0..\..\..\"
python .github\scripts\sync-claude-rules.py
pause
