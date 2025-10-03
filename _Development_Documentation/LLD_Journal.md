# Well-Bot · Low-Level Design — Journal Feature (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Overview

Interactive **journal overlay** (voice-first, text optional) runs a focused dialogue, then produces a **single-paragraph** entry. On manual cancel/abrupt end, summarize whatever content exists into a **draft** (tagged), unless there is **no transcript at all** (discard). Activity interruptions append an **“Activity interrupted”** card to the chat and resume conversation.

## 2) MCP Tools (Contracts)

Global request envelope (all tools):

```json
{ "trace_id":"string", "user_id":"uuid", "conversation_id":"uuid", "session_id":"uuid", "args":{}, "ts_utc":"ISO-8601" }
```

Standard response envelope (all tools):

```json
{
  "status":"ok"|"error",
  "type":"card"|"overlay_control"|"error_card",
  "title":"string",
  "body":"string",
  "meta":{ "kind":"journal"|"info" },
  "persisted_ids":{ "primary_id":"uuid","extra":[] },
  "diagnostics":{ "tool":"string","duration_ms":0 },
  "error_code":"string?"
}
```

### 2.1 `journal.start`

**Args**

```json
{ "mode":"voice|text|null", "opening_prompt":"string|null" }
```

**Behavior**

* Returns `overlay_control` → `{ "meta": { "overlay":"journal", "action":"open" } }`.
* Initializes a **journal overlay session** (client-scoped UUID; not persisted).
* VAD turn-taking inside overlay (3.0s silence).
  **Errors**: `JOURNAL_ALREADY_OPEN`.

### 2.2 `journal.stop`

**Args**

```json
{ "save": true }
```

* `save=true`: close overlay and begin summarization → `overlay_control` `{ "action":"close_and_summarize" }`.
* `save=false`: close overlay. Default follow-up is **Save Draft** unless explicit Discard was chosen in UI.
* If not open → `JOURNAL_NOT_OPEN`.

### 2.3 Summarization Policy (client-side step before save)

* Model: **DeepSeek** (no reasoning), `temperature=0.3`.
* Input: overlay transcript (user + assistant). **6000-character cap** applied to transcript **keeping the most recent content** (truncate oldest first).
* Draft rule: if total **user utterance length == 0** after trim → **discard** (no save). Otherwise summarize **whatever is available** into a draft.
* Output JSON (first-person; 120–180 words; topics now):

```json
{ "title":"<=80 chars", "body":"<=1500 chars", "mood":1, "topics":["tag1","tag2"] }
```

* Extraction: `mood ∈ [1..5]`; `0<topics<=5`, each `<=24 chars`, lowercase, no emojis/hashtags.

### 2.4 `journal.save`

**Args**

```json
{
  "summary": { "title":"string","body":"string","mood":1,"topics":["..."] },
  "is_draft": true|false
}
```

**Server behavior**

1. Validate: `title<=80`, `body<=1500`, `topics<=5`, each topic `<=24`.
2. Persist to `wb_journal` with `is_draft`.
3. Create `wb_activity_event`:

   * `action:"draft_created"` when `is_draft=true`
   * `action:"created"` when `is_draft=false`
4. **Index on write** only when `is_draft=false` → insert vector in `wb_embeddings` with model flag `miniLM|e5`.
5. Response `type:"card"`: title **“Journal Draft Saved”** or **“Journal Saved”**, body shows `Title: "..."` + first 140 chars.
   **Idempotency**: duplicate `trace_id` → replay last success.
   **Errors**: `VALIDATION_ERROR`, `LLM_SUMMARY_FAILED`, `DB_WRITE_FAILED`.

### 2.5 Interruption/Discard Cards (applies to all activities)

**Info card (interruption)**

* **Title**: `Activity interrupted`
* **Body**: `That activity didn’t complete. We saved what we could and you can continue chatting. You can review it anytime on your Dashboard.`
* **TTS**: `That activity didn’t complete, but we can keep chatting.`

**Discard card**

* **Title**: `Journal discarded.`
* **Body**: `No entry was saved.`

## 3) Overlay UI (Behavioral)

* **Stop controls** (buttons + voice intents):

  * **Save & Summarize** → `journal.stop(save=true)` then `journal.save(is_draft=false)`.
  * **Save Draft** (default on manual cancel and on inactivity) → `journal.stop(save=false)` then `journal.save(is_draft=true)`.
  * **Discard** → `journal.stop(save=false)` with explicit discard flag; no save.
* **End intents recognized**: “end journal”, “stop journal”, “I’m done”, “save this”.
* **VAD**: 3.0s silence to yield turn; no TTS barge-in.

## 4) Timeouts

* **Overlay inactivity**: prompt at **2:00** (“Still journaling?”); auto-**Save Draft** at **3:00**.
* **Session-level inactivity**: governed by global FSM (20s → 30s → 35s end), separate from overlay VAD.

## 5) Safety

* Run `safety.check` on each user utterance in overlay. On trigger:

  * Pause overlay agent; show **Support card** for ~5s; log `wb_safety_event`; resume overlay afterward.
  * If user ends after support, normal stop flow applies.

## 6) Data Model (tables)

All new tables prefixed `wb_`. Timestamps = `timestamptz` (UTC).

* **wb_journal**
  `{ id uuid pk, user_id uuid fk, title text, body text, mood int, topics text[], is_draft bool default false, created_at timestamptz, updated_at timestamptz }`
  Index: `(user_id, created_at desc)`

* **wb_activity_event**
  `{ id uuid pk, user_id uuid fk, type text, ref_id uuid, action text, created_at timestamptz }`
  Index: `(user_id, created_at desc)`

* **wb_embeddings** (finalized entries only)
  `{ id uuid pk, user_id uuid, kind 'journal', ref_id uuid, vector, model_tag 'miniLM'|'e5', created_at timestamptz }`
  Index: `(user_id, kind, ref_id)`

## 7) Editing & Re-indexing

* Dashboard permits editing **title/body/mood/topics** for **drafts and finalized entries**.
* On **finalized entry edits**, re-generate embedding vector (same model flag currently active) and **upsert** in `wb_embeddings`.
* On **draft edits**, do **not** embed; on **finalize action** (flip `is_draft=false` without re-summarization), embed then.

## 8) Logging

* **wb_tool_invocation_log**: log all `journal.*` with `status`, `duration_ms`, `error_code?`, `payload_size`.
* **wb_session_log**: overlay contributes to `avg_latency_ms`, possibly `reason_ended`.
* **wb_safety_event**: `{ id, session_id, ts, lang, action_taken, user_acknowledged, redacted_phrase }`.
  Retention: 30 days (configurable).

## 9) Validation & Normalization

* Title/body/topic constraints as above.
* **Topic normalization**: `trim → lowercase → collapse spaces → replace spaces with '-' → dedupe`.
* Reject empty summaries only if both `title` and `body` are empty after trim.

## 10) LLM Prompts (concise)

**Overlay agent (system)**

> Warm, concise, one or two questions at a time. Reflect feelings; do not advise or diagnose. Goal: help the user articulate thoughts for one paragraph later. Keep turns short.

**Summarizer (system)**

> You are a journal summarizer. Write one reflective paragraph in **first person** (120–180 words) capturing feelings, triggers, and one gentle next step. No advice/diagnoses. Output JSON exactly as:
> `{ "title": "", "body": "", "mood": 1, "topics": [] }`

## 11) Error Codes (canonical)

`JOURNAL_ALREADY_OPEN`, `JOURNAL_NOT_OPEN`, `VALIDATION_ERROR`, `LLM_SUMMARY_FAILED`, `DB_WRITE_FAILED`, `INTERRUPTED`, `NO_TRANSCRIPT`.

## 12) Acceptance (feature)

* Start/Stop overlay works (buttons + voice intents).
* Interruption info card appears + TTS line.
* Manual cancel default = **Save Draft**; Discard only on explicit choice.
* Drafts visible on Dashboard (editable); not embedded.
* Final entries saved, indexed, report card appended to chat with title + snippet.
* Safety card triggers & resumes overlay.
* Idempotent saves via `trace_id`.
