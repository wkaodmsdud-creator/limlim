@echo off
title Drug Info Search Site
cd /d "%~dp0"
echo ============================================
echo   Starting Drug Info Search Site...
echo   (yagmul jeongbo geomsaek site)
echo ============================================
echo.
echo   Your browser will open automatically.
echo   Keep this black window OPEN while using the site.
echo   Closing this window will STOP the server.
echo ============================================
echo.
start "" http://localhost:8080
py app.py
echo.
echo Server stopped. Press any key to close.
pause >nul
