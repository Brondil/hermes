@echo off
:: Run PoE2 Rumor Counter on Windows 11
:: This script checks for Python, installs dependencies if needed, and starts the app.

echo ============================================
echo    PoE2 Rumor Counter - Launcher (Windows)
echo ============================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python found. Checking dependencies...
echo.

:: Check if PyQt6 is installed
python -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing dependencies (this may take a few minutes)...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install dependencies.
        pause
        exit /b 1
    )
)

echo.
echo Starting PoE2 Rumor Counter...
echo Press Ctrl+C or close this window to stop the application.
echo.
python main.py
pause
