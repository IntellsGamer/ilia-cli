@echo off
if not exist ilia.bat (
    echo Could not find initial cli files to set up.
    echo.
    pause
    goto EOF
)
if exist "%appdata%\ilia-cli" (
    if not exist "%appdata%\ilia-cli\available.inf" (
        rmdir /Q /S "%appdata%\ilia-cli"
        if exist "%appdata%\ilia-cli" (
            echo Another instance of the CLI is installed incorrectly and we couldn't automatically fix the issue.
            echo.
            pause
            goto EOF
        )
    ) else (
        echo The CLI is already installed.
        echo.
        pause
        goto EOF
    )
)

title Schematic Deploy v0.1 - Installer

copy ilia.bat "C:\Users\%username%"
mkdir "%appdata%\ilia-cli\templates"
xcopy /E .\templates "%appdata%\ilia-cli\templates" >nul || goto :error
copy "%appdata%\ilia-cli\templates\available.inf" "%appdata%\ilia-cli" >nul || goto :error
del /F /Q "%appdata%\ilia-cli\templates\available.inf" >nul || goto :error

echo Successfully installed ^<ilia^> to user folder.
echo Try opening a folder and running ^<ilia^> command.
echo.
echo If it does not run, check if "ilia.bat" exists in "C:\Users\%username%"
echo If you see the file there, it means that your user home folder is not added to system PATH.
echo.
echo If you do not see the file, please submit a bug report.
echo.
pause >nul
goto EOF

:error
echo Could not copy templates to the archive.
echo Please check for missing permissions / denied access of read or copy of ^<templates^> folder
echo.
pause
goto EOF

:EOF