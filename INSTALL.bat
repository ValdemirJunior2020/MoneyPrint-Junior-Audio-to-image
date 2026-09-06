@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist logs mkdir logs
set LOG=logs\install.log
echo ==== Install started %date% %time% ====>>"%LOG%"
call :check git "Git"
call :check python "Python"
call :check node "Node.js"
call :check npm "npm"
call :check ffmpeg "FFmpeg"
call :check ffprobe "FFprobe"
call :check ollama "Ollama"
call :check docker "Docker (optional)"
echo.
echo Checking Ollama...
powershell -NoProfile -Command "try { Invoke-RestMethod -TimeoutSec 3 http://localhost:11434/api/tags | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo [WARN] Ollama server is not reachable.
  echo [WARN] Ollama server unreachable>>"%LOG%"
) else (
  echo [OK] Ollama server reachable.
  ollama list | findstr /i "qwen3:8b" >nul
  if errorlevel 1 (echo [WARN] qwen3:8b missing. Run: ollama pull qwen3:8b) else echo [OK] qwen3:8b found.
)
where python >nul 2>nul
if errorlevel 1 goto :missing
where npm >nul 2>nul
if errorlevel 1 goto :missing
if not exist .venv (
  python -m venv .venv >>"%LOG%" 2>&1
  if errorlevel 1 goto :failed
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >>"%LOG%" 2>&1
python -m pip install -r backend\requirements.txt >>"%LOG%" 2>&1
if errorlevel 1 goto :failed
pushd frontend
call npm install >>"..\%LOG%" 2>&1
if errorlevel 1 (popd & goto :failed)
popd
if not exist storage\projects mkdir storage\projects
echo Installation finished successfully.
pause
exit /b 0
:check
where %~1 >nul 2>nul
if errorlevel 1 (echo [MISSING] %~2 & echo [MISSING] %~2>>"%LOG%") else echo [OK] %~2
exit /b 0
:missing
echo Python and npm are required. Install the missing item, then rerun INSTALL.bat.
pause
exit /b 1
:failed
echo INSTALL FAILED. Read %LOG%
echo INSTALL FAILED %date% %time%>>"%LOG%"
pause
exit /b 1
