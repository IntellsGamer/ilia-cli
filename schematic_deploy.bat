@echo off
if not exist "%appdata%\ilia-cli\available.inf" (
    echo The application is not meant to be runned as a portable CLI.
    echo Please install the CLI via installer.bat if it is available.
    echo.
    pause
    goto EOF
)
title Schematic Deploy v0.1
echo === Schematic Deployer ===
echo.
echo  Select desired template
echo   Available templates:
echo.
echo        1^) HTML
echo        2^) Flask
echo.
CHOICE /C 12 /M "Which one"
echo.

if %errorlevel%==1 (
    echo Applying template...
    xcopy /E "%appdata%\ilia-cli\templates\html" . >nul || goto :error
    echo Done.
) else if %errorlevel%==2 (
    echo Applying template...
    xcopy /E "%appdata%\ilia-cli\templates\flask" . >nul || goto :error
    echo Done.
    start /wait "" "cmd /c py -m pip install -r requirements.txt" && start "" "cmd /k py app.py && echo. && echo. && echo To re-run the website, execute ^<py app.py^>
)
echo.
echo === Schematic Deployer ===
echo.
goto EOF

:error
echo Could not copy templates from archive to the root folder.
echo Please check for missing permissions.
echo.
pause
goto EOF

:EOF