# Well-Bot System Architecture

## Overview
Well-Bot is a wellness assistant application that provides REST API endpoints alongside Model Context Protocol (MCP) tools for comprehensive wellness support. The system integrates speech processing (STT/TTS), LLM capabilities, and various wellness tools through a modular architecture.

## System Components

### 1. Scripts (`/scripts/`)

| Script | Purpose | Workflow |
|--------|---------|----------|
| `test_llm_integration.py` | **LLM Integration Testing** - Comprehensive testing of the `/llm/chat:turn` endpoint with various input scenarios | 1. Connect to FastAPI server (localhost:8080)<br>2. Test small talk scenarios<br>3. Test tool intents (todo, journal, meditation, etc.)<br>4. Test safety triggers<br>5. Measure performance and success rates<br>6. Generate test summary with timing analysis |
| `stt_ws_sanity.py` | **STT WebSocket Testing** - CLI tool for testing Deepgram STT WebSocket streaming with WAV files | 1. Accept WAV file path as argument<br>2. Validate WAV format (mono, 16-bit)<br>3. Connect to STT WebSocket endpoint<br>4. Stream audio chunks to Deepgram<br>5. Receive and display transcript messages<br>6. Handle partial/final transcripts and errors |

### 2. API Layer (`/src/backend/api/`)

| Component | Purpose | Workflow |
|-----------|---------|----------|
| `main.py` | **FastAPI Application Bootstrap** - Main application entry point with CORS, logging, and router configuration | 1. Load environment variables<br>2. Configure structured logging (JSON format)<br>3. Create FastAPI app with metadata<br>4. Add CORS middleware for frontend<br>5. Include health, speech, and LLM routers<br>6. Provide root endpoint with API info<br>7. Start uvicorn server with reload |
| `routes/health.py` | **Health Check Endpoints** - Provides liveness and readiness probes for monitoring | 1. `/healthz` - Basic service status (no dependencies)<br>2. `/readyz` - Comprehensive readiness check<br>3. Test database connectivity<br>4. Validate Deepgram API key configuration<br>5. Return overall system health status |
| `routes/speech.py` | **Speech Processing Endpoints** - STT and TTS smoke test routes for audio processing | 1. `/speech/tts:test` - Synthesize text to MP3 audio<br>2. `/speech/stt:test` - WebSocket endpoint for real-time transcription<br>3. Handle concurrent audio streaming to Deepgram<br>4. Relay transcript messages back to client<br>5. Support PCM16 audio format with proper parameters |
| `routes/llm.py` | **LLM Chat Turn Handler** - Main conversational AI endpoint with safety-first pipeline | 1. Receive chat turn request with user text<br>2. Run safety check (50ms timeout, fail-open)<br>3. Detect intent using hybrid regex + LLM approach<br>4. Route to small-talk (DeepSeek) or stub cards (tool intents)<br>5. Return standardized card envelope with diagnostics |

### 3. Core Services (`/src/backend/core/`)

| Component | Purpose | Workflow |
|-----------|---------|----------|
| `intent_detector.py` | **Hybrid Intent Detection** - Fast-path regex patterns with LLM classifier fallback for user intent recognition | 1. Initialize regex patterns for common intents<br>2. Try regex fast-paths first (high confidence)<br>3. Fallback to LLM classifier if no regex match<br>4. Extract arguments from text based on intent<br>5. Return intent, confidence, and extracted args<br>6. Fail-open to small_talk on errors |

### 4. Services Layer (`/src/backend/services/`)

| Component | Purpose | Workflow |
|-----------|---------|----------|
| `deepseek.py` | **DeepSeek LLM Integration** - OpenAI SDK adapter for DeepSeek API with streaming support and intent classification | 1. Initialize client with DeepSeek base URL and API key<br>2. Support both streaming and non-streaming completions<br>3. Provide intent classification using structured prompts<br>4. Handle streaming fallback to non-streaming on errors<br>5. Mask user text for privacy-first logging<br>6. Return chat completions or intent classifications |
| `deepgram_stt.py` | **Speech-to-Text Service** - Deepgram WebSocket client for real-time audio transcription | 1. Initialize client with API key and configuration<br>2. Build WebSocket URLs with audio format parameters<br>3. Parse Deepgram transcript messages into normalized events<br>4. Handle interim and final transcript results<br>5. Support multiple audio formats (PCM16, etc.) |
| `deepgram_tts.py` | **Text-to-Speech Service** - Deepgram HTTP client for audio synthesis | 1. Initialize client with voice model and format settings<br>2. Send HTTP POST requests to Deepgram TTS API<br>3. Handle different voice models and audio formats<br>4. Return raw audio data (MP3, etc.)<br>5. Provide error handling for API failures |
| `database.py` | **Database Management** - Supabase client singleton with health checks and table access testing | 1. Initialize singleton Supabase client with service key<br>2. Provide health check via lightweight table query<br>3. Test access to specific tables<br>4. Handle connection errors gracefully<br>5. Return structured health status information |

### 5. MCP Tools (`/src/backend/mcp_tools/`)

| Component | Purpose | Workflow |
|-----------|---------|----------|
| `app.py` | **FastMCP Server Application** - Bootstrap server with middleware and tool registration following ADD_MCP.md pattern | 1. Configure structured logging<br>2. Create FastMCP app instance<br>3. Register global middlewares (timing, auth, envelope, error)<br>4. Register all wellness tools with proper names<br>5. Start server on configured host/port |
| `envelopes.py` | **Global Envelope Models** - Standardized request/response models for MCP tools following Global LLD requirements | 1. Define MCPRequest envelope with trace_id, user_id, args<br>2. Define Card response envelope with status, type, title, body<br>3. Provide helper functions for ok_card, error_card, overlay_control<br>4. Include Diagnostics and PersistedIds models<br>5. Ensure compatibility with Global LLD structure |
| `tools/safety_tool.py` | **Safety Check Tool** - Content safety analysis with support resource provision | 1. Extract text, language, and context from request<br>2. Check for concerning phrases (self-harm, suicide, etc.)<br>3. Return support resources if concerns found<br>4. Provide crisis hotline information<br>5. Return "no concerns" if safe content detected |
| `tools/todo_tool.py` | **Todo Management Tool** - CRUD operations for todo items with placeholder implementation | 1. `add` - Add todo items with title normalization<br>2. `list` - Display open todo items<br>3. `complete` - Mark items as completed<br>4. `delete` - Remove items from list<br>5. Return standardized card responses with mock data |

## Data Flow Architecture

### 1. Chat Turn Processing Pipeline
```
User Input → Safety Check → Intent Detection → Route Decision → Response Generation → Card Envelope
```

### 2. Speech Processing Pipeline
```
Audio Input → WebSocket → Deepgram STT → Transcript Events → Client Response
Text Input → HTTP Request → Deepgram TTS → Audio Data → MP3 Response
```

### 3. MCP Tool Processing Pipeline
```
MCP Request → Middleware Chain → Tool Execution → Card Response → Client
```

## Key Design Patterns

1. **Fail-Open Architecture**: Safety checks and LLM calls fail gracefully to prevent system blocking
2. **Hybrid Intent Detection**: Fast regex patterns with LLM fallback for optimal performance
3. **Singleton Services**: Database and API clients use singleton pattern for resource efficiency
4. **Structured Logging**: JSON-formatted logs with privacy-first text masking
5. **Standardized Envelopes**: Consistent request/response models across all MCP tools
6. **Concurrent Processing**: WebSocket relays handle bidirectional audio streaming efficiently

## Integration Points

- **Frontend**: CORS-enabled for Vite dev server (localhost:5173)
- **Database**: Supabase with service role key authentication
- **LLM**: DeepSeek API via OpenAI SDK with base URL override
- **Speech**: Deepgram API for both STT (WebSocket) and TTS (HTTP)
- **MCP**: FastMCP framework for tool registration and middleware

## Performance Characteristics

- **Safety Check**: 50ms timeout with fail-open behavior
- **Intent Detection**: Regex fast-path (~1ms) with LLM fallback (~500ms)
- **Chat Completion**: Streaming enabled with non-streaming fallback
- **Database**: Lightweight health checks with <1000ms response time
- **Audio Processing**: Real-time WebSocket streaming with concurrent relays
