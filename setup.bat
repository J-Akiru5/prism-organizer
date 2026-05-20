@echo off
echo.
echo  ====================================
echo   Prism Organizer - Setup
echo  ====================================
echo.
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed!
    echo  Please install Python from https://python.org
    echo.
    pause
    exit /b 1
)
echo  [OK] Python found
echo  Installing Prism Organizer...
echo.
pip install -e . 
if errorlevel 1 (
    echo.
    echo  [ERROR] Installation failed!
    pause
    exit /b 1
)
echo.
echo  ====================================
echo   Installation Complete!
echo  ====================================
echo.
echo  Run: prism-organizer --help
echo.
pause
