@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0RMPP-ScreenBridge.exe" (
    "%~dp0RMPP-ScreenBridge.exe" --uninstall
    exit /b %ERRORLEVEL%
)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1" -Uninstall
if errorlevel 1 (
    echo.
    echo Uninstaller could not start. Read the error above.
    pause
    exit /b 1
)
exit /b 0
