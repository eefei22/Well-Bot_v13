<!-- 389ae1eb-8404-46ff-a11a-461438344f2c 2a34155c-91b6-48d8-b2be-727ba15b105c -->
# Deepgram STT/TTS Backend Integration (Smoke Test)

### Scope

- Add env/config, service adapters, minimal API routes, extend readiness, and a tiny CLI sanity check. Keep logic minimal; no full session or tools wiring yet.

### Files to Add

- `src/backend/services/deepgram_stt.py`
- `src/backend/services/deepgram_tts.py`
- `src/backend/api/routes/speech.py`
- `scripts/stt_ws_sanity.py` (CLI sanity)

### Files to Edit

- `src/backend/api/main.py` — include `speech` router
- `src/backend/api/routes/health.py` — add Deepgram readiness
- `.env.example` or env loader — add `DEEPGRAM_API_KEY` (and optional defaults)

### Configuration

- Add `DEEPGRAM_API_KEY` to env loader.
- Optional defaults: `DEEPGRAM_STT_MODEL=nova-2`, `DEEPGRAM_LANGUAGE=en`, `DEEPGRAM_PUNCTUATE=true`, `DEEPGRAM_INTERIM_RESULTS=true`, `DEEPGRAM_SMART_FORMAT=true`, `DEEPGRAM_TTS_VOICE=aura-asteria-en`, `DEEPGRAM_TTS_FORMAT=mp3`, `DEEPGRAM_TTS_RATE=1.0`.
- STT WS endpoint: `wss://api.deepgram.com/v1/listen`
- TTS HTTP endpoint: `https://api.deepgram.com/v1/speak?model={DEEPGRAM_TTS_VOICE}`; set `Accept: audio/mpeg` for mp3 output.

### Service Adapters

- `services/deepgram_stt.py`
- Async client that connects to Deepgram WS with `Authorization: Token <DEEPGRAM_API_KEY>` and query params derived from env defaults (language=en, punctuate=true, interim_results=true, smart_format=true, model=env or default).
- Expose: `async def stream_transcripts(audio_iterable, **overrides) -> AsyncIterator[TranscriptEvent]` which:
- Opens WS, concurrently:
- Sends incoming PCM bytes from `audio_iterable` (assumes 16-bit PCM, 1ch; caller controls chunking).
- Reads Deepgram messages, yields normalized events: `{is_final: bool, text: str, channel: int|None, confidence: float|None, raw: dict}`.
- Handles reconnect with exponential backoff on transient failures; stops cleanly on final.
- `services/deepgram_tts.py`
- `async def synthesize(text: str, *, voice: str|None=None, format: str|None=None, rate: float|None=None) -> bytes`
- POST to Speak endpoint with `Authorization: Token <DEEPGRAM_API_KEY>`, JSON body `{"text": text}`; 
- Query/model param derives from `voice` (default `aura-asteria-en`), `Accept` derived from `format` (default mp3). Return raw audio bytes.
- Optional: if `rate` provided, include vendor-supported param when available (no-op if not supported).

### Minimal API Routes

- `api/routes/speech.py`
- `POST /speech/tts:test`
- Input: optional JSON `{"text": "..."}`; default: "Hello from Well-Bot".
- Calls `deepgram_tts.synthesize(...)` and returns `Response(content=audio, media_type="audio/mpeg")`.
- `WS /speech/stt:test`
- Accepts WS; client sends binary PCM chunks.
- The route proxies chunks to Deepgram via `deepgram_stt.stream_transcripts(...)` and relays back JSON messages like `{type: "partial"|"final", text, confidence, channel}` as they arrive.
- On `final`, include a placeholder call-site for `safety.check` (comment + log only for now).

### Readiness

- Extend `GET /readyz` to include `deepgram` key:
- Perform a lightweight metadata probe `GET https://api.deepgram.com/v1/me` with auth.
- Report `{status: "ok"|"error", latency_ms, error?}`. Overall readiness remains gated by DB as today, but now includes Deepgram.

### CLI Sanity (local)

- `scripts/stt_ws_sanity.py`:
- Usage: `python scripts/stt_ws_sanity.py path/to/sample.wav`
- Opens the WAV (mono), streams PCM frames to `ws://localhost:8080/speech/stt:test`, prints partials and finals; exits when EOS.

### Hook Points

- In `WS /speech/stt:test`, add a placeholder comment and structured log for where `safety.check` would be invoked on final transcripts. No tool wire-up yet.
- Leave a TODO in `deepgram_tts.py` noting that TTS should be muted during meditation playback later.

### Notes

- Defaults per request: `language=en`, `punctuate=true`, `interim_results=true`, `smart_format=true`.
- We’ll accept both `punctuation` and `punctuate` in config but send `punctuate` to Deepgram.
- Sample rate/encoding: the smoke path assumes client provides PCM16 mono; we’ll document this in the WS route docstring.

### To-dos

- [ ] Add DEEPGRAM_API_KEY and Deepgram defaults to env loader
- [ ] Create Deepgram STT adapter with WS streaming and reconnect
- [ ] Create Deepgram TTS adapter with HTTP synthesize
- [ ] Add speech routes: POST /speech/tts:test and WS /speech/stt:test
- [ ] Extend readiness to include Deepgram metadata probe
- [ ] Add CLI WAV streamer for WS STT sanity
- [ ] Add placeholder/log for safety.check on final transcripts