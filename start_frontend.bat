@echo off
echo Starting Well-Bot Frontend Server...
echo.

REM Kill any processes on ports 5173-5179 (Vite's typical port range)
echo Cleaning up ports 5173-5179...
for /L %%i in (5173,1,5179) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%i') do (
        if not "%%a"=="" (
            echo Killing process %%a on port %%i
            taskkill /PID %%a /F >nul 2>&1
        )
    )
)

echo.
echo Starting frontend on port 5173...
REM Start the frontend development server on port 5173
npm run dev -- --port 5173

pause
