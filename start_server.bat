@echo off
title Inventory Management Server (Production)
echo ============================================
echo   Inventory Management Server - Production
echo   Using Waitress (multi-threaded)
echo ============================================
echo.

cd /d "%~dp0"

python -c "import waitress" 2>nul
if errorlevel 1 (
    echo [Setup] Installing Waitress...
    pip install waitress
    echo.
)

echo Starting server in production mode...
echo.
python server.py --production
pause
