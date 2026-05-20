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
where prism-organizer >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] The 'prism-organizer' command is not on your system PATH.
    echo  This is common on Windows if the Python Scripts directory is not configured.
    echo.
    echo  You can still run the tool directly using:
    echo      python -m prism_organizer --help
    echo.
    echo  To run it as 'prism-organizer', add the Python Scripts directory to your PATH:
    echo  e.g., %%APPDATA%%\Python\Python313\Scripts
) else (
    echo  Run: prism-organizer --help
)
echo.
pause

