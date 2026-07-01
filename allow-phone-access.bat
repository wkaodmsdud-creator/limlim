@echo off
title Allow Phone Access (Firewall - run once)
rem --- self-elevate to admin ---
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting administrator permission...
    echo Please click YES on the popup.
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)
rem --- now running as admin: add firewall rule ---
netsh advfirewall firewall delete rule name="DrugInfoSite 8080" >nul 2>&1
netsh advfirewall firewall add rule name="DrugInfoSite 8080" dir=in action=allow protocol=TCP localport=8080 profile=private,domain
echo.
echo ============================================
echo   DONE! Phone access is now allowed.
echo   You only need to run this ONCE.
echo ============================================
echo.
echo Press any key to close.
pause >nul
