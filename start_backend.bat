@echo off
echo Starting Well-Bot Backend Server...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Start the backend server
python -m uvicorn src.backend.api.main:app --reload --port 8000

pause
