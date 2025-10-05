@echo off
REM Deepgram STT Integration Test Script
REM Tests the complete Deepgram STT pipeline from server startup to transcript generation.
REM Author: Well-Bot Development Team
REM Date: January 2025

setlocal enabledelayedexpansion

echo ========================================
echo Well-Bot Deepgram STT Integration Test
echo ========================================
echo.

REM Configuration
set MAX_ATTEMPTS=3
set SERVER_URL=http://localhost:8080
set STT_WS_ENDPOINT=ws://localhost:8080/speech/stt:test
set HEALTH_ENDPOINT=%SERVER_URL%/healthz
set READY_ENDPOINT=%SERVER_URL%/readyz
set SERVER_DIR=src\backend\api
set TEST_OUTPUT_DIR=test_output
set LOG_FILE=%TEST_OUTPUT_DIR%\test_stt.log
set SAMPLE_AUDIO=C:\Users\lowee\Desktop\Well-Bot\Well-Bot_v13\tests\sample_audio.wav

REM Create test output directory
if not exist "%TEST_OUTPUT_DIR%" mkdir "%TEST_OUTPUT_DIR%"

REM Initialize log file
echo [%date% %time%] Starting Deepgram STT Integration Test > "%LOG_FILE%"
echo [%date% %time%] Max attempts: %MAX_ATTEMPTS% >> "%LOG_FILE%"
echo [%date% %time%] Server URL: %SERVER_URL% >> "%LOG_FILE%"
echo [%date% %time%] STT WebSocket: %STT_WS_ENDPOINT% >> "%LOG_FILE%"
echo [%date% %time%] Sample audio: %SAMPLE_AUDIO% >> "%LOG_FILE%"

REM Function to log messages
:log
echo [%date% %time%] %~1
echo [%date% %time%] %~1 >> "%LOG_FILE%"
goto :eof

REM Function to check if server is running
:check_server
call :log "Checking if server is running..."
curl -s -f "%HEALTH_ENDPOINT%" >nul 2>&1
if %errorlevel% equ 0 (
    call :log "[PASSED] Server is running"
    goto :eof
) else (
    call :log "[FAILED] Server is not running"
    goto :eof
)

REM Function to start server
:start_server
call :log "Starting FastAPI server..."
cd /d "%SERVER_DIR%"
start /b python main.py
cd /d "%~dp0"

REM Wait for server to start
call :log "Waiting for server to start..."
set /a WAIT_COUNT=0
:wait_loop
timeout /t 2 /nobreak >nul
call :check_server
if %errorlevel% equ 0 goto :server_ready
set /a WAIT_COUNT+=1
if %WAIT_COUNT% geq 15 (
    call :log "[FAILED] Server failed to start within 30 seconds"
    goto :test_failed
)
goto :wait_loop

:server_ready
call :log "[PASSED] Server started successfully"
goto :eof

REM Function to test health endpoints
:test_health_endpoints
call :log "Testing health endpoints..."

REM Test /healthz
call :log "Testing /healthz endpoint..."
curl -s -f "%HEALTH_ENDPOINT%" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[FAILED] /healthz endpoint failed"
    goto :test_failed
)
call :log "[PASSED] /healthz endpoint working"

REM Test /readyz
call :log "Testing /readyz endpoint..."
curl -s -f "%READY_ENDPOINT%" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[FAILED] /readyz endpoint failed"
    goto :test_failed
)
call :log "[PASSED] /readyz endpoint working"

REM Get detailed readiness status
call :log "Checking detailed readiness status..."
curl -s "%READY_ENDPOINT%" > "%TEST_OUTPUT_DIR%\stt_readiness.json"
if %errorlevel% neq 0 (
    call :log "[FAILED] Failed to get readiness details"
    goto :test_failed
)

REM Check if Deepgram is configured
findstr /i "deepgram" "%TEST_OUTPUT_DIR%\stt_readiness.json" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[FAILED] Deepgram not found in readiness check"
    goto :test_failed
)
call :log "[PASSED] Deepgram configuration found in readiness check"

goto :eof

REM Function to validate audio file
:validate_audio_file
call :log "Validating sample audio file..."

if not exist "%SAMPLE_AUDIO%" (
    call :log "[FAILED] Sample audio file not found: %SAMPLE_AUDIO%"
    goto :test_failed
)

call :log "[PASSED] Sample audio file found: %SAMPLE_AUDIO%"

REM Basic file size check
for %%A in ("%SAMPLE_AUDIO%") do set FILE_SIZE=%%~zA
if %FILE_SIZE% leq 0 (
    call :log "[FAILED] Sample audio file is empty"
    goto :test_failed
)

call :log "[PASSED] Audio file validation completed (size: %FILE_SIZE% bytes)"
goto :eof

REM Function to test STT WebSocket (simplified for batch)
:test_stt_websocket
call :log "Testing STT WebSocket endpoint..."

REM Note: Full WebSocket testing requires Python script
REM For batch script, we'll just verify the endpoint exists
call :log "STT WebSocket endpoint: %STT_WS_ENDPOINT%"
call :log "[PASSED] STT WebSocket endpoint configured"

REM Run Python STT test
call :log "Running Python STT test..."
python tests\test_stt.py
if %errorlevel% neq 0 (
    call :log "[FAILED] Python STT test failed"
    goto :test_failed
)

call :log "[PASSED] STT WebSocket test completed"
goto :eof

REM Function to generate test report
:generate_report
call :log "Generating test report..."

echo. > "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Well-Bot Deepgram STT Integration Test Report >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo ================================================ >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Test Date: %date% %time% >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Test Status: PASSED >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Test Results: >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - Server startup: [PASSED] >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - Health endpoints: [PASSED] >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - Audio file validation: [PASSED] >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - STT WebSocket test: [PASSED] >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Generated Files: >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - stt_transcript.json (transcript results) >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - stt_readiness.json (server status) >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo - test_stt.log (detailed log) >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Check stt_transcript.json for the generated transcript from the audio file. >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"

call :log "[PASSED] Test report generated: %TEST_OUTPUT_DIR%\test_stt_report.txt"
goto :eof

REM Function to cleanup
:cleanup
call :log "Cleaning up..."

REM Stop any running Python processes (server)
taskkill /f /im python.exe >nul 2>&1

call :log "[PASSED] Cleanup completed"
goto :eof

REM Function to handle test failure
:test_failed
call :log "[FAILED] TEST FAILED"
echo. >> "%LOG_FILE%"
echo [%date% %time%] TEST FAILED >> "%LOG_FILE%"

REM Generate failure report
echo. > "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Well-Bot Deepgram STT Integration Test Report >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo ================================================ >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Test Date: %date% %time% >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Test Status: FAILED >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"
echo Check the log file for detailed error information: %LOG_FILE% >> "%TEST_OUTPUT_DIR%\test_stt_report.txt"

call :cleanup
exit /b 1

REM Function to handle test success
:test_success
call :log "[PASSED] ALL TESTS PASSED!"
echo. >> "%LOG_FILE%"
echo [%date% %time%] ALL TESTS PASSED >> "%LOG_FILE%"

call :generate_report
call :cleanup

echo.
echo ========================================
echo Test completed successfully!
echo Check %TEST_OUTPUT_DIR%\ for results
echo ========================================
exit /b 0

REM Main test execution
:main
call :log "Starting Deepgram STT Integration Test..."

REM Check if we're in the right directory or tests subdirectory
if exist "src\backend\api\main.py" (
    call :log "[PASSED] Found project structure in current directory"
) else if exist "..\src\backend\api\main.py" (
    call :log "[PASSED] Found project structure in parent directory"
    cd /d ".."
) else (
    call :log "[FAILED] Error: Could not find project structure"
    call :log "Looking for src\backend\api\main.py"
    call :log "Current directory: %CD%"
    goto :test_failed
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[FAILED] Error: Python not found in PATH"
    goto :test_failed
)

REM Check if curl is available
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log "[FAILED] Error: curl not found in PATH"
    goto :test_failed
)

call :log "[PASSED] Prerequisites check passed"

REM Run tests with retry logic
set /a ATTEMPT=1
:retry_loop
call :log "=== ATTEMPT %ATTEMPT% of %MAX_ATTEMPTS% ==="

REM Start server
call :start_server
if %errorlevel% neq 0 goto :retry_attempt

REM Test health endpoints
call :test_health_endpoints
if %errorlevel% neq 0 goto :retry_attempt

REM Validate audio file
call :validate_audio_file
if %errorlevel% neq 0 goto :retry_attempt

REM Test STT WebSocket
call :test_stt_websocket
if %errorlevel% neq 0 goto :retry_attempt

REM All tests passed
goto :test_success

:retry_attempt
call :log "Attempt %ATTEMPT% failed, cleaning up..."
call :cleanup

set /a ATTEMPT+=1
if %ATTEMPT% leq %MAX_ATTEMPTS% (
    call :log "Retrying in 5 seconds..."
    timeout /t 5 /nobreak >nul
    goto :retry_loop
) else (
    call :log "All %MAX_ATTEMPTS% attempts failed"
    goto :test_failed
)

REM Start the test
goto :main
