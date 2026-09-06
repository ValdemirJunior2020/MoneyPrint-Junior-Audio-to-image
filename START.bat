@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run INSTALL.bat first.
  pause
  exit /b 1
)
if not exist frontend\node_modules (
  echo Run INSTALL.bat first.
  pause
  exit /b 1
)
start "Audio-to-Image API" cmd /k "cd /d ""%~dp0"" && call .venv\Scripts\activate.bat && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
start "Audio-to-Image UI" cmd /k "cd /d ""%~dp0frontend"" && npm run dev -- --host 127.0.0.1"
timeout /t 3 >nul
start "" http://localhost:5173
