@echo off
REM Installation script for Windows

REM Check if Python 3.8+ is available
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed or not in PATH. Please install Python 3.8 or higher.
    exit /b 1
)

REM Create a virtual environment
echo Creating virtual environment...
python -m venv venv

REM Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies with requirements.txt (includes the demucs fork)
echo Installing dependencies (this may take a while)...
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Installation complete!
echo.
echo To start the application:
echo 1. Activate the virtual environment: venv\Scripts\activate.bat
echo 2. Run the application: python main.py
echo.
echo To exit the virtual environment when done: deactivate
