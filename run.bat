@echo off
:: Poe 2 Vorana's Saga Rumor Tracker - launcher for Windows
:: Fix working dir and use pure ASCII

setlocal

:: Resolve the directory where THIS batch file lives (handles shortcuts/favorites)
set "_SCRIPT_DIR=%~dp0"
cd /d "%_SCRIPT_DIR%"

echo.
echo ====================================
echo    Poe 2 Rumor Tracker Launcher    
echo ====================================
echo.

:: Check Python exists
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found! Install Python 3.10+ first.
    pause
    exit /b 1
)

echo [OK] Python:
python --version
echo.

:: Check if dependencies are installed
pip show opencv-python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [!] Dependencies not installed. Installing from requirements.txt...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo [ERROR] Failed to install dependencies.
        echo Try: python -m pip --upgrade pip
        pause
        exit /b 1
    )
    echo.
    echo [OK] Dependencies installed!
)

echo [i] Starting Poe2 Rumor Tracker...
python main.py %*

echo.
echo Press Enter to close...
pause >nul