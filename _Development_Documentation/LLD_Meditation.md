# Well-Bot · Low-Level Design — Meditation Feature (MVP)

*Last updated: 2025-10-03 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Scope

* Chat ops: **play**, **cancel**, **restart**; client logs outcome via **log**.
* All videos are **~3 minutes**; selection is **random among active variants** (request phrasing does not change duration).
* Supports **two providers**: Supabase file or **YouTube embed** (provider-aware player).
* TTS: speak a single intro line, then **mute assistant TTS during playback** (video audio only).
* Barge-in: **only for cancel** (pause → Yes/No confirm). **Restart** has no confirm.
* On end/cancel/restart, append a **report card** and resume chat with a brief check-in prompt (no numeric rating stored).
* Standard **“Activity interrupted”** card on errors/interruptions; conversation continues.

## 2) Data Model

**wb_meditation_video**
`{ id uuid pk, uri text, label text, active boolean default true, provider enum('supabase','youtube') default 'supabase', youtube_id text null, duration_seconds int null }`
Index: `(active)`, unique constraint recommended on `(provider, youtube_id)` when `provider='youtube'`.

**wb_meditation_log**
`{ id uuid pk, user_id uuid fk, video_id uuid fk, started_at timestamptz, ended_at timestamptz null, outcome text check in ('completed','canceled'), created_at timestamptz default now() }`
Index: `(user_id, created_at desc)`

**wb_activity_event**
`{ id uuid pk, user_id uuid fk, type 'meditation', ref_id uuid, action 'started'|'completed'|'canceled'|'restarted', created_at timestamptz }`

> No embeddings for meditation.

## 3) Session & Audio Behavior

* **Session FSM suspension**: while video is playing, **suspend** 20/30/35s inactivity prompts; resume FSM after end/cancel/restart.
* **Intro line**: before playback, assistant speaks: “Starting your 3-minute meditation.”
* **During playback**: assistant TTS muted; video audio only.
* **Cancel**: pause video → confirm “Stop the session now?” (Yes/No; 5s timeout = No/resume).
* **Restart**: restart current video at 0s; no confirmation.

## 4) MCP Tools (Contracts)

Global envelopes per project standard.

### 4.1 `meditation.play`

**Args**

```json
{ "reason": "user_request" }
```

**Behavior**

1. Select a random `video_id` from `wb_meditation_video where active=true`.
2. Emit `overlay_control` to **open** the provider-aware player and start the video.
   *If provider = `youtube`: use IFrame Player via `youtube-nocookie.com` with `enablejsapi=1`, `controls=0`, `modestbranding=1`; after the intro line, call `playVideo()` (if autoplay blocked, show a “Tap to start” overlay button).
   *If provider = `supabase`: use `<video>` element and `play()`.*
3. Create `wb_activity_event(type='meditation', action='started', ref_id=video_id)`.
4. Client records `started_at=now()` for later logging.
   **Failure fallback**: if the chosen video fails to load/play within **3s** (player error or stalled start), try another active video; if all fail → **error card** “Meditation unavailable right now.” and resume chat.

**Response**

```json
{
  "status": "ok",
  "type": "overlay_control",
  "title": "Meditation",
  "body": "Starting your 3-minute meditation.",
  "meta": {
    "overlay": "meditation",
    "action": "open",
    "video_id": "<uuid>",
    "provider": "youtube|supabase",
    "youtube_id": "<id-if-youtube-or-null>",
    "playback_url": "<uri>"
  }
}
```

### 4.2 `meditation.cancel`

**Args**

```json
{}
```

**Behavior**

* Pause playback (`pauseVideo()` for YouTube, `video.pause()` for Supabase); show confirm **Yes/No** (buttons + voice Yes/No).
* **Yes** → stop playback (`stopVideo()` / pause+reset), close overlay, append **Canceled** card, client calls `meditation.log`.
* **No/timeout (5s)** → resume playback (`playVideo()` / `video.play()`).

**Response (on confirm Yes)**

```json
{
  "status":"ok","type":"card","title":"Meditation canceled",
  "body":"Session ended early at <local time>.",
  "meta":{ "kind":"meditation" }
}
```

### 4.3 `meditation.restart`

**Args**

```json
{}
```

**Behavior**

* Restart the **same** video from 0s (no confirmation).
  *YouTube:* `seekTo(0,true); playVideo();`
  *Supabase:* `currentTime=0; play()`
* Emit `wb_activity_event(action='restarted')`.

**Response**

```json
{
  "status":"ok","type":"overlay_control",
  "title":"Meditation",
  "body":"Restarting your 3-minute meditation.",
  "meta":{ "overlay":"meditation","action":"restart" }
}
```

### 4.4 `meditation.log`

**Args**

```json
{ "video_id":"uuid","started_at":"ISO-8601","ended_at":"ISO-8601","outcome":"completed"|"canceled" }
```

**Behavior**

* Persist to `wb_meditation_log`.
* Emit `wb_activity_event(action=outcome)`.

**Response (completed)**

```json
{
  "status":"ok","type":"card","title":"Meditation finished",
  "body":"You completed a 3-minute session at <local time>.",
  "meta":{ "kind":"meditation" },
  "persisted_ids":{ "primary_id":"<log_id>" }
}
```

## 5) Cards & UX

* **Completed card**: Title `Meditation finished`; Body `You completed a 3-minute session at <local time>.`
* **Canceled card**: Title `Meditation canceled`; Body `Session ended early at <local time>.`
* After either card, assistant (TTS on again) asks a brief, non-numeric check-in (e.g., “How are you feeling now?”).
* **Interruption**: standard project “Activity interrupted” card and resume chat.

## 6) Safety & Guardrails

* Safety is not expected to trigger during playback; still run `safety.check` on user utterances **before** play and during confirm prompts. On trigger, show **support card** and do not start/continue playback.

## 7) Logging

* **wb_tool_invocation_log**: all `meditation.*` calls (status, duration_ms, error_code?, payload_size).
* **wb_activity_event**: `started|completed|canceled|restarted`.
* **wb_meditation_log**: outcome + timestamps.
  Retention: 30 days.

## 8) Acceptance

* `meditation.play` opens a **provider-aware** overlay (Supabase `<video>` or YouTube IFrame), plays a random active **~3-min** video, mutes assistant during playback, and suspends session inactivity prompts.
* `meditation.cancel` pauses and confirms; Yes closes overlay and shows **Canceled** card; No resumes.
* `meditation.restart` restarts the same video instantly (no confirm).
* On end/cancel, client calls `meditation.log`; **Completed** card shown for success, **Canceled** for early end.
* After card, assistant asks a brief non-numeric check-in.
* Failure fallback: alternate video selection or error card after 3s total load failures.
* Interruption card shown when appropriate; chat resumes.
