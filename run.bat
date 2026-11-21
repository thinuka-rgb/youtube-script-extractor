@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" youtube_transcript.py %*
if errorlevel 1 goto failed
pause
exit /b 0
:failed
echo.
echo Could not finish. Read the error above and the README troubleshooting guide.
pause
exit /b 1
