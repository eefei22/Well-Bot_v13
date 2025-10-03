# Well-Bot · Low-Level Design — Safety (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Scope & Behavior

* **Coverage:** all user utterances across the app (main chat, journal overlay, meditation prompts).
* **Language:** EN for MVP (case-insensitive match with light stemming).
* **Action:** on trigger → **pause current feature**, show **Support Resources** card for ~5s (visible + audible), then **resume** where possible (journal overlay, chat, or meditation confirm flow).
* **Cool-down:** after a trigger, suppress new cards for **2 minutes** unless a **higher-severity** phrase appears.

## 2) Detection Rules (Keyword/Phrase List)

* Base tokens (stemmed): `suicide`, `kill myself`, `want to die`, `end it all`, `self harm`, `hurt myself`, `cut myself`, `jump off`, `no reason to live`, `take my life`.
* Simple combos: (`want|going|plan|thinking`) + (`die|kill myself|end it`).
* Negation guard (reduce false positives): if within ±4 tokens of `not|never|no intention`, lower severity.
* **Severity levels:**

  * `SI_INTENT` (explicit intent, e.g., “I want to kill myself”)
  * `SI_IDEATION` (thoughts, e.g., “sometimes I want to die”)
  * `SELF_HARM` (non-suicidal self-harm terms)

> Rule list is modular (JSON config) and hot-reloadable for future expansion.

## 3) MCP Tool — `safety.check`

Global envelopes per project standard.

**Args**

```json
{ "text": "string", "lang": "en", "context": "chat|journal|meditation", "session_ts": "ISO-8601" }
```

**Response (no trigger)**

```json
{ "status":"ok", "type":"card", "title":"", "body":"", "meta":{ "kind":"info", "action":"none" } }
```

**Response (trigger)**

```json
{
  "status":"ok",
  "type":"card",
  "title":"Support Resources",
  "body":"If you’re struggling or thinking about self-harm, consider talking to a counselor or contacting local emergency services. You’re not alone.",
  "meta":{ "kind":"info", "action":"show_support_card", "severity":"SI_INTENT|SI_IDEATION|SELF_HARM" },
  "diagnostics":{ "tool":"safety.check", "duration_ms":0 }
}
```

**Client handling**

* On `show_support_card`:

  * **Pause** current activity (stop TTS; pause journal/meditation if active).
  * Display card for ~5s with an **“OK”** button (sets `user_acknowledged=true`).
  * Resume activity (or stay in chat) afterward.

## 4) Logging & Privacy

* **wb_safety_event**
  `{ id uuid pk, session_id uuid fk, ts timestamptz, lang text, action_taken text, user_acknowledged bool, redacted_phrase text, severity text }`

  * `redacted_phrase`: **masked snippet** (e.g., “want to [redacted]”), plus the matched **category/severity**.
* **wb_tool_invocation_log**: log `safety.check` calls with `status`, `duration_ms`.
* Retention: **30 days** (configurable).

## 5) UX (Visible + Audible)

* **Card copy (default)**
  Title: `Support Resources`
  Body: `If you’re struggling or thinking about self-harm, consider talking to a counselor or contacting local emergency services. You’re not alone.`
  Button: `OK`

* **TTS line:** “I’m here with you. I’ll show some support options. We can keep talking.”

* **Resume behavior:** After card closes (or OK pressed), return to the prior context:

  * **Chat:** continue listening.
  * **Journal:** overlay remains open; agent offers a gentle, non-directive check-in line.
  * **Meditation:** remain paused if card was shown during confirm; user can choose to proceed or cancel.

## 6) Debounce & Escalation

* **Debounce window:** 2 minutes. Within this window, **suppress duplicate cards** of same or lower severity.
* **Escalation:** If a higher severity phrase is detected (e.g., `SI_INTENT` after `SI_IDEATION`), **show a new card** and update log.

## 7) Integration Points

* **Main chat pipeline:** run `safety.check` on **every user utterance** before intent routing/tool calls.
* **Journal overlay:** check each user turn; pause overlay replies on trigger; show card; after ~5s, resume overlay.
* **Meditation:** check before `play`; during cancel prompt interactions, also check; do not interrupt active playback except at user interaction points.

## 8) Error Handling

* If `safety.check` fails (tool error), **fail-open** to normal flow but record a `wb_tool_invocation_log` error entry; do not block user, do not show stale cards.

## 9) Acceptance

* Triggers on configured phrases with case-insensitive, lightly stemmed matching.
* Shows support card (visible + audible), pauses current activity, resumes afterward.
* Debounce prevents repeated cards for 2 minutes unless severity escalates.
* Logs `wb_safety_event` with masked snippet and severity; captures `user_acknowledged`.
* Works in chat, journal overlay, and meditation flows.

