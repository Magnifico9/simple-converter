@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" install.py --remove
pause
