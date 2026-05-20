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
    set /p ADD_TO_PATH="Would you like to automatically add the Python Scripts directory to your User PATH? (Y/N): "
    if /i "%ADD_TO_PATH%"=="Y" (
        echo.
        echo  Adding to PATH...
        powershell -Command "$scriptsPath = & python -c 'import os, sysconfig; user = sysconfig.get_path(''scripts'', ''nt_user''); glob = sysconfig.get_path(''scripts''); print(user if os.path.exists(os.path.join(user, ''prism-organizer.exe'')) else glob)'; $userPath = [System.Environment]::GetEnvironmentVariable('PATH', 'User'); $paths = $userPath -split ';' | ForEach-Object { $_.Trim().TrimEnd('\') }; if ($paths -notcontains $scriptsPath.Trim().TrimEnd('\')) { $newUserPath = $userPath; if ($newUserPath -and -not $newUserPath.EndsWith(';')) { $newUserPath += ';' }; $newUserPath += $scriptsPath; [System.Environment]::SetEnvironmentVariable('PATH', $newUserPath, 'User'); Write-Output 'Successfully added to User PATH! Please restart your command prompt/terminal.' } else { Write-Output 'Path is already in User PATH.' }"
    ) else (
        echo.
        echo  You can still run the tool directly using:
        echo      python -m prism_organizer --help
        echo.
        echo  To run it as 'prism-organizer', add the Python Scripts directory to your PATH:
        echo  e.g., %%APPDATA%%\Python\Python313\Scripts
    )
) else (
    echo  Run: prism-organizer --help
)
echo.
pause

