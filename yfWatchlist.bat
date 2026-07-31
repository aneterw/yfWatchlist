@echo off
setlocal
cd /d "%~dp0"

REM Use pythonw so no terminal window appears.
REM If pythonw not in PATH, fall back to py -3 launcher.
where pythonw >nul 2>nul
if %ERRORLEVEL%==0 (
    start "" pythonw app_desktop.py
) else (
    start "" py -3 app_desktop.py
)

REM Show a brief confirmation; window auto-closes after 2s.
echo yfWatchlist launched.
timeout /t 2 /nobreak >nul
endlocal
