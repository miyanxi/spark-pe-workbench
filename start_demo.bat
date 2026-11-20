@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -B scripts\run_local.py
  goto finished
)
python -c "import sys" >nul 2>nul
if not errorlevel 1 (
  python -B scripts\run_local.py
  goto finished
)
py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
  py -3 -B scripts\run_local.py
  goto finished
)
echo Python was not found. Install Python 3.11, then install backend/requirements.txt.
:finished
echo.
pause
