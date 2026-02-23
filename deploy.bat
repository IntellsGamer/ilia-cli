@echo off
:: deploy.bat - Force deploy ilia CLI files to user folder
:: No prompts, no verification, just deploy

:: echo 🔧 Deploying ilia CLI files...

:: Force copy schematic_deploy.py to user folder
xcopy /Y "%~dp0\schematic_deploy.py" "%USERPROFILE%\schematic_deploy.py" >nul
if %errorlevel% equ 0 (
    echo schematic_deploy.py copied to: %USERPROFILE%
) else (
    echo Failed to copy schematic_deploy.py
)

:: Force copy ilia.bat to user folder
xcopy /Y "%~dp0\ilia.bat" "%USERPROFILE%\ilia.bat" >nul
if %errorlevel% equ 0 (
    echo ilia.bat copied to: %USERPROFILE%
) else (
    echo Failed to copy ilia.bat
)

echo.