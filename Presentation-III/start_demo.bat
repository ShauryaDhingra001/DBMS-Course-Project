
@echo off
cd /d "%~dp0"
echo Starting Laboratory Equipment Management System...
echo.
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Package installation failed.
    echo Check whether Python is installed and try again.
    pause
    exit /b 1
)
python demo_db.py
if errorlevel 1 (
    echo.
    echo ERROR: Demo database setup failed.
    pause
    exit /b 1
)
python app.py
pause
