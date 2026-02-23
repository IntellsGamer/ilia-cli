@echo off
:: ilia Telemetry Server Startup Script (Windows)

set PORT=3001
set HOST=127.0.0.1
set LOG_DIR=telemetry_logs
set PYTHON_EXE=python

echo [INFO] Starting ilia Telemetry Server...

:: Create directories
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
if not exist "logs" mkdir "logs"

:: Check if port is in use
netstat -ano | findstr ":%PORT%" | findstr "LISTENING" > nul
if %errorlevel% equ 0 (
    echo [WARN] Port %PORT% is already in use
    echo        Finding existing process...
    
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%" ^| findstr "LISTENING"') do (
        set "PID=%%a"
    )
    
    if defined PID (
        echo        Found process with PID: %PID%
        set /p choice=   Kill existing process? (y/N): 
        if /i "!choice!"=="y" (
            taskkill /PID %PID% /F > nul 2>&1
            timeout /t 2 /nobreak > nul
        ) else (
            echo [ERROR] Cannot start server. Port %PORT% is in use.
            pause
            exit /b 1
        )
    ) else (
        echo [ERROR] Could not determine process using port %PORT%
        pause
        exit /b 1
    )
)

:: Start Flask development server
echo [INFO] Starting Flask server on %HOST%:%PORT%...
echo        Logs: %LOG_DIR%

:: Start the server in a new window
start "ilia Telemetry Server" cmd /k "%PYTHON_EXE% telemetry_server.py --host %HOST% --port %PORT% --log-dir %LOG_DIR%"

echo [OK] Server is starting...
echo [URL] Server URL: http://%HOST%:%PORT%
echo [API] API Endpoint: http://%HOST%:%PORT%/ilia-cli/tm/submit
echo.
echo [INFO] Check the new console window for server logs
echo [INFO] Press any key to close this window...
pause > nul