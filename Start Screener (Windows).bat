@echo off
REM Double-click to set up (first time) and launch the screener on Windows.
cd /d "%~dp0"
echo ==================================================
echo    Sector Rotation Screener
echo ==================================================
echo.

REM 1. Python check
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed.
  echo Install it ^(free^) from https://www.python.org/downloads/  ^(version 3.11 or newer^).
  echo IMPORTANT: on the first install screen, tick "Add Python to PATH".
  echo Then double-click this file again.
  echo.
  pause
  exit /b 1
)

REM 2. Create the environment (first time only)
if not exist ".venv" (
  echo First-time setup: creating the Python environment ^(about a minute^)...
  python -m venv .venv
  if errorlevel 1 ( echo Could not create environment. & pause & exit /b 1 )
)

REM 3. Install packages
echo Checking required packages...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 ( echo Package install failed. Check your internet and try again. & pause & exit /b 1 )

REM 4. Stop any copy already running (prevents port conflicts / "Internal Server Error")
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8501 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul

REM 5. Open the browser shortly after the server starts
start "" cmd /c "timeout /t 6 >nul && start "" http://localhost:8501"

echo.
echo ==================================================
echo   [OK] The screener is running.
echo   It will open in your browser automatically.
echo   If it doesn't, open this link yourself:
echo.
echo         http://localhost:8501
echo.
echo   ^>^>^> KEEP THIS WINDOW OPEN while you use the app. ^<^<^<
echo   Closing this window stops the app (that's normal).
echo   To use it again later, just double-click this file.
echo ==================================================
echo.

REM 5. Run (config.toml makes this start with no prompts)
".venv\Scripts\python.exe" -m streamlit run app.py
pause
