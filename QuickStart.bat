@echo off
REM Double-click to set up (first time) and launch the screener on Windows.
cd /d "%~dp0"
echo ==================================================
echo    Sector Rotation Screener
echo ==================================================
echo.

 
 
REM 4. Stop any copy already running (prevents port conflicts / "Internal Server Error")
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8502 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>nul

REM 5. Open the browser shortly after the server starts
start "" cmd /c "timeout /t 6 >nul && start "" http://localhost:8502"

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
".venv\Scripts\python.exe" -m streamlit run app.py  --server.port 8502 
pause
