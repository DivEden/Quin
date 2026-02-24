@echo off
echo ========================================
echo   QUINIX TAB MANAGER - QUICK START
echo ========================================
echo.
echo Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found!
    echo Please install Python first. See SETUP-INSTRUCTIONS.txt
    echo.
    pause
    exit /b 1
)
echo Python found!
echo.
echo Checking Selenium...
pip show selenium >nul 2>&1
if errorlevel 1 (
    echo Selenium not installed. Installing now...
    pip install selenium
    if errorlevel 1 (
        echo ERROR: Failed to install Selenium
        echo Please run manually: pip install selenium
        echo.
        pause
        exit /b 1
    )
) else (
    echo Selenium already installed!
)
echo.
echo ========================================
echo   STARTING TAB MANAGER...
echo ========================================
echo.
python quinix_tab_manager.py
pause
