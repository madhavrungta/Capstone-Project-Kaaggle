@echo off
echo ===================================================
echo Starting VyaparSathi Market Intelligence Agent...
echo ===================================================
echo.
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://127.0.0.1:8000"
python main.py
pause


