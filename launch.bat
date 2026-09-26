@echo off
rem Opens ResumeBank in an Edge app window, starting the dev server first if needed.
setlocal
cd /d "%~dp0"
set "URL=http://127.0.0.1:8000/"

rem Reuse a server that's already running (e.g. started from VS Code).
curl -s -o nul "%URL%" && goto open

start "ResumeBank server" /min cmd /k ".venv\Scripts\python.exe manage.py runserver"

rem Wait up to ~30 s for the server to answer.
for /l %%i in (1,1,30) do (
    timeout /t 1 /nobreak >nul
    curl -s -o nul "%URL%" && goto open
)
echo ResumeBank server did not start - check the "ResumeBank server" window.
pause
exit /b 1

:open
start "" msedge --app=%URL%
