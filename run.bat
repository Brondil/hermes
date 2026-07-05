@echo off
@chcp 65001 >nul
title Poe 2 — Vorana's Saga Rumor Tracker - Nya~ (=\^·ω·\^=)

echo.
echo ================================
echo   Poe2 Rumor Tracker Launcher  
echo   by Neko-chan (=\^·ω·\^=) 
echo ================================
echo.

:: Check if running in virtual environment
if defined VIRTUAL_ENV (
    echo [OK] Virtualenv detected: %VIRTUAL_ENV%
) else (
    echo [!] Not in a virtualenv. Create one first:
    echo     python -m venv venv
    echo     Call the appropriate activate script, then run this again.
    echo.
)

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
     [OK] Dependencies installed! =)
)

echo [i] Starting Poe2 Rumor Tracker...
python main.py %*

echo.
echo Closing in 5 seconds. Press Ctrl+C to stop immediately.
timeout /t 5 >nul
