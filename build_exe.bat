@echo off
:: ============================================
:: PoE2 Rumor Counter - Build EXE script
:: Упаковывает проект в один исполняемый файл
:: ============================================
echo ============================================
echo    СБОРКА ИСПОЛНЯЕМОГО ФАЙЛА (.exe)
echo         PoE2 Rumor Counter
echo ============================================
echo.

:: Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не найден!
    echo Установите Python с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo.
echo [1/4] Проверка PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] PyInstaller не установлен. Установка...
    pip install pyinstaller
    if %errorlevel% neq 0 (
        echo ОШИБКА: Не удалось установить PyInstaller!
        pause
        exit /b 1
    )
)
echo   ✓ PyInstaller найден.

echo.
echo [2/4] Проверка зависимостей проекта...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ОШИБКА: Не удалось установить зависимости!
    pause
    exit /b 1
)
echo   ✓ Все зависимости установлены.

echo.
echo [3/4] Сборка проекта в один .exe файл...
echo Это может занять пару минут...
echo.
pyinstaller --onefile ^
    --windowed ^
    --name "PoE2 Rumor Counter" ^
    --add-data "requirements.txt;." ^
    --icon=^"" ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo ОШИБКА сборки PyInstaller!
    pause
    exit /b 1
)

echo   ✓ Сборка завершена успешно!

:: Копирование в build/
if not exist "build" mkdir build
copy dist\PoE2 Rumor Counter.exe build\ >nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка копирования в папку build/
) else (
    echo   ✓ Файл скопирован: build\PoE2 Rumor Counter.exe
)

:: Скрытие консоли для windowed режима
echo.
echo ============================================
echo         ГОТОВО! (.exe файл создан!)
echo ============================================
echo.
echo Исполняемый файл находится в папках:
echo   - dist\PoE2 Rumor Counter.exe  (оригинал)
echo   - build\PoE2 Rumor Counter.exe (копия)
echo.
echo Вы можете запустить его на любом компьютере с Windows!
echo Остальные файлы из папки проекта можно удалить, нужен только .exe
echo.
pause
