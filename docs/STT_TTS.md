# Deepgram STT/TTS Integration Tests

This directory contains comprehensive test scripts for the Deepgram Speech-to-Text (STT) and Text-to-Speech (TTS) integration.

## Services Overview

### Deepgram STT Service (`src/backend/services/deepgram_stt.py`)
- **Purpose**: Real-time speech-to-text transcription via WebSocket
- **Model**: nova-2 (enhanced/general)
- **Format**: Raw PCM16 frames (no RIFF header)
- **Parameters**: 
  - `encoding`: linear16
  - `sample_rate`: 44100 Hz
  - `channels`: 1 (mono)
  - `interim_results`: true
  - `smart_format`: true
  - `punctuate`: true
- **Output**: `TranscriptEvent` objects with text, confidence, and final/partial status

### Deepgram TTS Service (`src/backend/services/deepgram_tts.py`)
- **Purpose**: Text-to-speech synthesis via HTTP API
- **Voice**: aura-asteria-en (default)
- **Format**: MP3 audio
- **Parameters**: Configurable voice and audio format
- **Output**: Raw audio bytes (MP3)

### Speech Routes (`src/backend/api/routes/speech.py`)
- **TTS Endpoint**: `POST /speech/tts:test` - Synthesizes text to MP3 audio
- **STT Endpoint**: `WS /speech/stt:test` - Real-time audio transcription via WebSocket
- **Implementation**: Concurrent relay pattern for STT (client↔Deepgram↔server)

## Test Scripts

### TTS Tests

#### `tts_test.py` (Cross-platform)
Python script for comprehensive TTS testing.

**Usage:**
```bash
cd tests
python tts_test.py
```

**Features:**
- Server startup and health checks
- TTS synthesis with default and custom text
- Audio file validation (MP3 headers, size)
- Retry logic (3 attempts)
- Detailed logging and reporting

#### `tts_test.bat` (Windows)
Windows batch script wrapper for TTS testing.

**Usage:**
```cmd
cd tests
tts_test.bat
```

### STT Tests

#### `stt_test.py` (Cross-platform)
Python script for comprehensive STT testing with diagnostic capture.

**Usage:**
```bash
cd tests
python stt_test.py
```

**Features:**
- Server startup and health checks
- Audio file validation (WAV format, properties)
- WebSocket connection and audio streaming
- Real-time transcript capture
- Diagnostic information collection:
  - Deepgram WebSocket parameters
  - Client capture code details
  - Audio format information
  - First 5 message descriptors
  - Server logs
- Retry logic (3 attempts)
- Comprehensive reporting

#### `stt_test.bat` (Windows)
Windows batch script wrapper for STT testing.

**Usage:**
```cmd
cd tests
stt_test.bat
```

## Test Output

All test results are saved to `tests/output/` directory:

### TTS Test Output
- `tts_default.mp3` - Audio generated with default text
- `tts_custom.mp3` - Audio generated with custom text
- `health.json` - Server readiness status
- `tts.log` - Detailed test log
- `tts_report.txt` - Summary report

### STT Test Output
- `stt_result.json` - Complete transcript results with confidence scores
- `stt_health.json` - Server readiness status
- `stt_diag.json` - Diagnostic information (parameters, messages, etc.)
- `stt_diag.txt` - Human-readable diagnostic report
- `stt.log` - Detailed test log
- `stt_report.txt` - Summary report

## Technical Implementation

### STT WebSocket Relay Pattern
The STT implementation uses a concurrent relay pattern:

```python
# Two concurrent coroutines:
async def client_to_deepgram():
    # Forward client audio → Deepgram
    
async def deepgram_to_client():
    # Forward Deepgram transcripts → client

# Run concurrently:
await asyncio.gather(client_to_deepgram(), deepgram_to_client())
```

### Audio Format Handling
- **Input**: Raw PCM16 frames from `wave.readframes()` (no WAV header)
- **Deepgram Parameters**: `encoding=linear16`, `sample_rate=44100`, `channels=1`
- **Stream Control**: `{"type": "CloseStream"}` signal for finalization
- **Graceful Close**: 0.5s wait after CloseStream for processing

### Error Handling
- Comprehensive error logging with structured logging
- Graceful WebSocket disconnection handling
- Retry logic with exponential backoff
- Diagnostic capture for troubleshooting

## Environment Variables

Required environment variables:
```bash
DEEPGRAM_API_KEY=your_api_key_here
DEEPGRAM_STT_MODEL=nova-2
DEEPGRAM_LANGUAGE=en
DEEPGRAM_PUNCTUATE=true
DEEPGRAM_INTERIM_RESULTS=true
DEEPGRAM_SMART_FORMAT=true
DEEPGRAM_TTS_VOICE=aura-asteria-en
DEEPGRAM_TTS_FORMAT=mp3
```

## Prerequisites

```bash
pip install requests websockets aiohttp structlog
```

## Expected Results

**Success:**
```
✓ ALL TESTS PASSED!
Test completed successfully!
Check tests/output/ for results
```

**STT Success Indicators:**
- Interim transcripts within 1-2 seconds
- Final transcript after CloseStream
- Server logs show "DG RAW:" messages
- Client reports "Received X messages" instead of 0

**TTS Success Indicators:**
- MP3 files generated successfully
- Audio files have valid headers
- Server responds with 200 status
- Audio playback works correctly

## Troubleshooting

1. **Server won't start**: Check if port 8080 is available
2. **TTS fails**: Verify `DEEPGRAM_API_KEY` is set
3. **STT receives 0 messages**: Check audio format parameters
4. **Audio files empty**: Check Deepgram API quota and connectivity
5. **WebSocket errors**: Verify network connectivity to Deepgram

## Manual Testing

```bash
# Start server
cd src/backend/api
python main.py

# Test TTS endpoint
curl -X POST http://localhost:8080/speech/tts:test \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from Well-Bot"}' \
  -o test_audio.mp3

# Test health
curl http://localhost:8080/readyz
```

## Integration Notes

The services are designed for easy integration into the main Well-Bot system:

- **STT**: Use `get_stt_client()` for WebSocket connections
- **TTS**: Use `synthesize()` function for audio generation
- **Routes**: Include `speech_router` in FastAPI app
- **Health**: STT/TTS status included in `/readyz` endpoint
- **Safety**: Placeholder for `safety.check` on final transcripts