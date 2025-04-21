@echo off
REM Script to run Open Karaoke Studio

REM Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found. Please run install.bat first.
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Run the application
python main.py

REM Deactivate the virtual environment when done
deactivate
