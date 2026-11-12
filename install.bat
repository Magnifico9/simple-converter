@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python environment...
    python -m venv .venv || (echo Python 3.10+ is required. & pause & exit /b 1)
)
echo Installing Python libraries...
".venv\Scripts\python.exe" -m pip install -q --upgrade pip
".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
where ffmpeg >nul 2>nul || winget install --id Gyan.FFmpeg -e --silent --accept-package-agreements --accept-source-agreements
".venv\Scripts\python.exe" install.py
pause
