@echo off
REM Deepgram TTS Integration Test Script
REM Tests the complete Deepgram TTS pipeline from server startup to audio generation
REM Author: Well-Bot Development Team
REM Date: January 2025

setlocal enabledelayedexpansion

echo ========================================
echo Well-Bot Deepgram TTS Integration Test
echo ========================================
echo.

REM Configuration
set MAX_ATTEMPTS=3
set SERVER_URL=http://localhost:8080
set TTS_ENDPOINT=%SERVER_URL%/speech/tts:test
set HEALTH_ENDPOINT=%SERVER_URL%/healthz
set READY_ENDPOINT=%SERVER_URL%/readyz
set SERVER_DIR=src\backend\api
set TEST_OUTPUT_DIR=test_output
set LOG_FILE=%TEST_OUTPUT_DIR%\test_deepgram.log

REM Create test output directory
if not exist "%TEST_OUTPUT_DIR%" mkdir "%TEST_OUTPUT_DIR%"

REM Initialize log file
echo [%date% %time%] Starting Deepgram TTS Integration Test > "%LOG_FILE%"
echo [%date% %time%] Max attempts: %MAX_ATTEMPTS% >> "%LOG_FILE%"
echo [%date% %time%] Server URL: %SERVER_URL% >> "%LOG_FILE%"

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
    call :log "✓ Server is running"
    goto :eof
) else (
    call :log "✗ Server is not running"
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
    call :log "✗ Server failed to start within 30 seconds"
    goto :test_failed
)
goto :wait_loop

:server_ready
call :log "✓ Server started successfully"
goto :eof

REM Function to test health endpoints
:test_health_endpoints
call :log "Testing health endpoints..."

REM Test /healthz
call :log "Testing /healthz endpoint..."
curl -s -f "%HEALTH_ENDPOINT%" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ /healthz endpoint failed"
    goto :test_failed
)
call :log "✓ /healthz endpoint working"

REM Test /readyz
call :log "Testing /readyz endpoint..."
curl -s -f "%READY_ENDPOINT%" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ /readyz endpoint failed"
    goto :test_failed
)
call :log "✓ /readyz endpoint working"

REM Get detailed readiness status
call :log "Checking detailed readiness status..."
curl -s "%READY_ENDPOINT%" > "%TEST_OUTPUT_DIR%\readiness.json"
if %errorlevel% neq 0 (
    call :log "✗ Failed to get readiness details"
    goto :test_failed
)

REM Check if Deepgram is configured
findstr /i "deepgram" "%TEST_OUTPUT_DIR%\readiness.json" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ Deepgram not found in readiness check"
    goto :test_failed
)
call :log "✓ Deepgram configuration found in readiness check"

goto :eof

REM Function to test TTS endpoint
:test_tts_endpoint
call :log "Testing TTS endpoint..."

REM Test with default text
call :log "Testing TTS with default text..."
curl -s -X POST "%TTS_ENDPOINT%" -H "Content-Type: application/json" -o "%TEST_OUTPUT_DIR%\tts_default.mp3" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ TTS endpoint failed with default text"
    goto :test_failed
)

REM Check if we got audio data
if not exist "%TEST_OUTPUT_DIR%\tts_default.mp3" (
    call :log "✗ No audio file generated"
    goto :test_failed
)

REM Check file size (should be > 0)
for %%A in ("%TEST_OUTPUT_DIR%\tts_default.mp3") do set FILE_SIZE=%%~zA
if %FILE_SIZE% leq 0 (
    call :log "✗ Generated audio file is empty"
    goto :test_failed
)
call :log "✓ TTS endpoint working - Generated %FILE_SIZE% bytes of audio"

REM Test with custom text
call :log "Testing TTS with custom text..."
curl -s -X POST "%TTS_ENDPOINT%" -H "Content-Type: application/json" -d "{\"text\": \"Testing Well-Bot TTS integration\"}" -o "%TEST_OUTPUT_DIR%\tts_custom.mp3" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ TTS endpoint failed with custom text"
    goto :test_failed
)

REM Check custom audio file
if not exist "%TEST_OUTPUT_DIR%\tts_custom.mp3" (
    call :log "✗ No custom audio file generated"
    goto :test_failed
)

for %%A in ("%TEST_OUTPUT_DIR%\tts_custom.mp3") do set CUSTOM_FILE_SIZE=%%~zA
if %CUSTOM_FILE_SIZE% leq 0 (
    call :log "✗ Generated custom audio file is empty"
    goto :test_failed
)
call :log "✓ Custom TTS working - Generated %CUSTOM_FILE_SIZE% bytes of audio"

goto :eof

REM Function to test audio file validity
:test_audio_validity
call :log "Validating generated audio files..."

REM Check if files are valid MP3 (basic check)
call :log "Checking MP3 file headers..."
powershell -Command "& { $bytes = [System.IO.File]::ReadAllBytes('%TEST_OUTPUT_DIR%\tts_default.mp3'); if ($bytes[0] -eq 0xFF -and ($bytes[1] -band 0xE0) -eq 0xE0) { Write-Host 'Valid MP3 header found' } else { Write-Host 'Invalid MP3 header'; exit 1 } }" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ Default audio file has invalid MP3 header"
    goto :test_failed
)
call :log "✓ Default audio file has valid MP3 header"

powershell -Command "& { $bytes = [System.IO.File]::ReadAllBytes('%TEST_OUTPUT_DIR%\tts_custom.mp3'); if ($bytes[0] -eq 0xFF -and ($bytes[1] -band 0xE0) -eq 0xE0) { Write-Host 'Valid MP3 header found' } else { Write-Host 'Invalid MP3 header'; exit 1 } }" >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ Custom audio file has invalid MP3 header"
    goto :test_failed
)
call :log "✓ Custom audio file has valid MP3 header"

goto :eof

REM Function to generate test report
:generate_report
call :log "Generating test report..."

echo. > "%TEST_OUTPUT_DIR%\test_report.txt"
echo Well-Bot Deepgram TTS Integration Test Report >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo ================================================ >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Test Date: %date% %time% >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Test Status: PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Test Results: >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - Server startup: ✓ PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - Health endpoints: ✓ PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - TTS endpoint: ✓ PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - Audio generation: ✓ PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - Audio validation: ✓ PASSED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Generated Files: >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - tts_default.mp3 (%FILE_SIZE% bytes) >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - tts_custom.mp3 (%CUSTOM_FILE_SIZE% bytes) >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - readiness.json >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo - test_deepgram.log >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo You can play the generated MP3 files to verify TTS quality. >> "%TEST_OUTPUT_DIR%\test_report.txt"

call :log "✓ Test report generated: %TEST_OUTPUT_DIR%\test_report.txt"
goto :eof

REM Function to cleanup
:cleanup
call :log "Cleaning up..."

REM Stop any running Python processes (server)
taskkill /f /im python.exe >nul 2>&1

call :log "✓ Cleanup completed"
goto :eof

REM Function to handle test failure
:test_failed
call :log "✗ TEST FAILED"
echo. >> "%LOG_FILE%"
echo [%date% %time%] TEST FAILED >> "%LOG_FILE%"

REM Generate failure report
echo. > "%TEST_OUTPUT_DIR%\test_report.txt"
echo Well-Bot Deepgram TTS Integration Test Report >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo ================================================ >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Test Date: %date% %time% >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Test Status: FAILED >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo. >> "%TEST_OUTPUT_DIR%\test_report.txt"
echo Check the log file for detailed error information: %LOG_FILE% >> "%TEST_OUTPUT_DIR%\test_report.txt"

call :cleanup
exit /b 1

REM Function to handle test success
:test_success
call :log "✓ ALL TESTS PASSED!"
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
call :log "Starting Deepgram TTS Integration Test..."

REM Check if we're in the right directory or tests subdirectory
if exist "src\backend\api\main.py" (
    call :log "✓ Found project structure in current directory"
) else if exist "..\src\backend\api\main.py" (
    call :log "✓ Found project structure in parent directory"
    cd /d ".."
) else (
    call :log "✗ Error: Could not find project structure"
    call :log "Looking for src\backend\api\main.py"
    call :log "Current directory: %CD%"
    goto :test_failed
)

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ Error: Python not found in PATH"
    goto :test_failed
)

REM Check if curl is available
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    call :log "✗ Error: curl not found in PATH"
    goto :test_failed
)

call :log "✓ Prerequisites check passed"

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

REM Test TTS endpoint
call :test_tts_endpoint
if %errorlevel% neq 0 goto :retry_attempt

REM Test audio validity
call :test_audio_validity
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
