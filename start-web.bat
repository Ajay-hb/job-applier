@echo off
echo.
echo  =============================================
echo   Job Applier Web UI - Starting...
echo  =============================================
echo.
cd /d "%~dp0"
python web\server.py
pause
