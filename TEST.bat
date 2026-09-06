@echo off
setlocal
cd /d "%~dp0"
if not exist logs mkdir logs
set LOG=logs\test.log
if not exist .venv\Scripts\python.exe (
  echo [FAIL] Python environment missing.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pytest -q backend\tests >>"%LOG%" 2>&1
if errorlevel 1 (
  echo [FAIL] Backend tests failed. See %LOG%
  pause
  exit /b 1
)
echo [PASS] Backend tests actually ran.
pushd frontend
call npm run build >>"..\%LOG%" 2>&1
if errorlevel 1 (
  popd
  echo [FAIL] Frontend build failed. See %LOG%
  pause
  exit /b 1
)
popd
echo [PASS] Frontend build actually ran.
pause
