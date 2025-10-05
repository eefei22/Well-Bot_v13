Great—this log is super telling. You did stream 90 binary chunks and then sent your “close” signal, but your client received **0 messages** back and timed out. That means:

1. your server isn’t relaying Deepgram messages back to the client, **and/or**
2. Deepgram never finalized because it wasn’t told your stream was PCM (so it can’t decode), **and/or**
3. you didn’t send Deepgram the end-of-stream control (`CloseStream`).

Below is a drop-in fix that covers all three.

---

# ✅ What to change (do all three)

## A) Tell Deepgram what you’re sending

Your test is sending **raw PCM16 frames** (you’re reading WAV frames, which exclude the header). So don’t set `container="wav"`. Instead, declare:

* `encoding="linear16"`
* `sample_rate=44100`
* `channels=1`

(If you ever decide to stream the **WAV file bytes including the RIFF header**, then set `container="wav"` and keep the same sample_rate/channels. But with `wave.readframes(...)` you’re sending raw PCM.)

## B) Actually forward Deepgram events back to the client

You need a **concurrent read loop** from Deepgram → client. Without it, your client will always see 0 messages.

## C) Explicitly close the Deepgram stream

After the last audio chunk, send `{"type":"CloseStream"}` to Deepgram (or close the DG WS cleanly). Otherwise you’ll sit waiting for a final result that never comes.

---

# 🧩 FastAPI WebSocket relay (server) — reliable template

```python
# api/routes/speech.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio, json
import websockets

router = APIRouter()

DG_URL = "wss://api.deepgram.com/v1/listen"
DG_HEADERS = [("Authorization", f"Token {YOUR_DEEPGRAM_API_KEY}")]

# helper to open a Deepgram WS; returns the connection
async def open_deepgram_ws(params: dict):
    # pass params via querystring; you can also send them as a JSON "configure" frame after connect
    from urllib.parse import urlencode
    qs = urlencode({k: v for k, v in params.items() if v is not None})
    uri = f"{DG_URL}?{qs}"
    return await websockets.connect(uri, extra_headers=DG_HEADERS, max_size=None)

@router.websocket("/speech/stt:test")
async def stt_test(websocket: WebSocket):
    await websocket.accept()

    # IMPORTANT: matches your test (raw PCM16 frames @ 44.1k mono)
    dg_params = {
        "model": "nova-2",
        "language": "en",
        "interim_results": True,
        "smart_format": True,
        "encoding": "linear16",
        "sample_rate": 44100,
        "channels": 1,
    }

    dg = await open_deepgram_ws(dg_params)

    async def client_to_deepgram():
        try:
            while True:
                msg = await websocket.receive()
                if msg.get("type") == "websocket.receive":
                    if msg.get("bytes") is not None:
                        await dg.send(msg["bytes"])  # binary to Deepgram
                    elif msg.get("text") is not None:
                        # optional simple protocol
                        if msg["text"].lower() == "stop":
                            await dg.send(json.dumps({"type": "CloseStream"}))
                            break
                else:
                    # client closed
                    await dg.send(json.dumps({"type": "CloseStream"}))
                    break
        except WebSocketDisconnect:
            try:
                await dg.send(json.dumps({"type": "CloseStream"}))
            except:
                pass

    async def deepgram_to_client():
        try:
            async for message in dg:  # Deepgram sends TEXT frames (JSON)
                # Forward as-is to your client (test harness)
                await websocket.send_text(message)
        except Exception:
            # dg closed or network issue
            pass

    await asyncio.gather(client_to_deepgram(), deepgram_to_client())

    try:
        await dg.close()
    except:
        pass
```

**Why this fixes your trace:**

* Deepgram can parse your PCM only when you declare `encoding/sample_rate/channels`.
* The concurrent loop ensures transcripts (interim + final) actually reach your test client.
* `CloseStream` ensures you get a final in <~1–2s for your 2.1s clip.

---

# 🔧 Your Python test client (keep, just add “stop” & right pacing)

You’re sending 1024-frame chunks at 44.1 kHz. Real-time pacing is ≈ **1024/44100 ≈ 23ms** per chunk. You currently `sleep(0.01)` (~10ms), which is faster than real time. Not fatal, but let’s match real-time to be safe, and send a final “stop” text frame.

```python
# minimal WS test client (Python)
import asyncio, wave, websockets

async def run():
    uri = "ws://localhost:8080/speech/stt:test"
    async with websockets.connect(uri, max_size=None) as ws:
        with wave.open("tests/sample_audio.wav", "rb") as wavf:
            chunk_frames = 1024
            rate = wavf.getframerate()  # 44100
            bytes_per_frame = wavf.getsampwidth() * wavf.getnchannels()
            real_time_sleep = chunk_frames / rate  # ~0.023s

            while True:
                frames = wavf.readframes(chunk_frames)
                if not frames:
                    break
                await ws.send(frames)  # binary
                await asyncio.sleep(real_time_sleep)

        # signal end-of-stream to server
        await ws.send("stop")

        # read a few messages to confirm
        try:
            for _ in range(10):
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                print("EVENT:", msg[:200], "...")
        except asyncio.TimeoutError:
            print("No events within timeout")

asyncio.run(run())
```

---

# 🧪 Quick sanity checks

1. **HTTP one-shot**: send `sample_audio.wav` to Deepgram’s HTTP API. If transcript returns, your key/model are fine; remaining issues are only in WS handling.

2. **First events logging** (server): log the **first 3** messages received from Deepgram. If you see them in server logs but not in the client, your forward loop isn’t running or is erroring.

3. **Remove buffering**: don’t collect all chunks then process; stream them straight through and forward events as they arrive (as above).


---

Additional speech.py checks

Your structure is *very* close, and it’s clear you’ve done most of the right things. The reason your test still returns **0 messages** is due to two subtle issues inside this exact file.

---

## 🧩 Root causes in your current `speech.py`

### 1. **Wrong container parameter for raw PCM**

```python
"container": "wav",
"encoding": "linear16",
```

You’re reading WAV *frames* in your client, meaning **no RIFF header** is sent.
When Deepgram sees `"container": "wav"` but receives headerless PCM, it just waits forever, never emitting any transcript.

➡ **Fix:**
Use the raw PCM settings instead:

```python
"encoding": "linear16",
"sample_rate": 44100,
"channels": 1,
# remove container
```

---

### 2. **Your relay exits before Deepgram can emit anything**

You have this in your `deepgram_to_client()`:

```python
if transcript_event.is_final:
    ...
    break  # End after first final transcript for smoke test
```

That `break` kills the task as soon as it sees a “final” (but in your current run you never get one).
If your audio finishes before Deepgram emits anything, this loop simply waits forever until the **client_to_deepgram()** task ends, which then closes the Deepgram connection without ever forwarding any message.

➡ **Fix:**

* Remove that `break` entirely for testing.
* Let it keep streaming until `CloseStream` acknowledgment or the Deepgram WS naturally closes.

---

### 3. **No confirmation that `CloseStream` was sent**

In your logs, the client does `await websocket.send("stop")`, but your handler checks for:

```python
if text.lower() == "stop" or text == '{"type": "CloseStream"}':
```

Good.
However, you never flush or await `dg_ws.wait_closed()` afterward — Deepgram might still be processing when your server closes.

➡ **Fix:**
After `await dg_ws.send(json.dumps({"type": "CloseStream"}))`, wait briefly or close gracefully:

```python
await asyncio.sleep(0.5)
await dg_ws.wait_closed()
```

---

## ✅ Minimal working edit (apply inside your file)

Replace your `dg_params` block and remove the premature break:

```python
# Deepgram parameters matching raw PCM16 input
dg_params = {
    "model": "nova-2",
    "language": "en",
    "interim_results": True,
    "smart_format": True,
    "punctuate": True,
    "encoding": "linear16",
    "sample_rate": 44100,
    "channels": 1,
}
```

Then, inside `deepgram_to_client()`:

```python
# REMOVE this line:
# break  # End after first final transcript for smoke test
```

And inside `client_to_deepgram()`, after sending CloseStream:

```python
await dg_ws.send(json.dumps({"type": "CloseStream"}))
await asyncio.sleep(0.5)
await dg_ws.wait_closed()
```

---

## 🧪 Quick verification checklist

| Check                                                       | Expected result                                |
| ----------------------------------------------------------- | ---------------------------------------------- |
| 1️⃣ Deepgram receives correct encoding/sample rate          | Transcript events start appearing within 1–2 s |
| 2️⃣ Client log shows `Received event 1 from Deepgram...`    | ✅                                              |
| 3️⃣ Server doesn’t close before transcript                  | ✅                                              |
| 4️⃣ Test harness reports “Received X messages” instead of 0 | ✅                                              |

---

## ⚠️ Optional: Debug tip

Add:

```python
async for message in dg_ws:
    logger.info(f"DG RAW: {message}")
```

just before parsing — if you see JSON coming through but still “0 messages”, the problem is only in `_parse_transcript_message`.

---

After these three adjustments (`remove container`, `don’t break early`, `graceful close`), your next run should yield **at least one Deepgram transcript event** and clear the timeout.
