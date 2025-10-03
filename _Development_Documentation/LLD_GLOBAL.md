# Well-Bot · Low-Level Design — Global (MVP)

*Last updated: 2025-10-02 · Timestamps stored in UTC; UI timezone Asia/Kuala_Lumpur (UTC+8).*

This document compiles the global glue and module LLDs into one implementation-ready reference.

---

## 0) Tech & Runtime

* **Client**: React+Vite (Chrome-first), MCP **client** UI.
* **Speech**: Deepgram streaming **STT** (partials+punctuation), **TTS** (neutral; 1.0x).
* **LLM**: DeepSeek (no “reasoning” mode), temp 0.3 for tool+chat.
* **Data**: Supabase (Auth/Postgres/Storage), `pgvector`.
* **Embeddings**: default **all-MiniLM-L6-v2**; alt **e5-small-v2** via config flag (both index+query).

---

## 1) Global Envelopes (All MCP Tools)

**Request**

```json
{ "trace_id":"string", "user_id":"uuid", "conversation_id":"uuid", "session_id":"uuid",
  "args":{}, "ts_utc":"ISO-8601" }
```

**Response**

```json
{
  "status":"ok"|"error",
  "type":"card"|"overlay_control"|"error_card",
  "title":"string","body":"string",
  "meta":{ "kind":"journal|gratitude|todo|quote|meditation|info" },
  "persisted_ids":{ "primary_id":"uuid","extra":[] },
  "diagnostics":{ "tool":"string","duration_ms":0 },
  "error_code":"string?"
}
```

**Error card**

```json
{ "type":"error_card","title":"Action failed","body":"Cause and next step","meta":{"tool":"<tool>","error_code":"<code>"} }
```

---

## 2) Session FSM & Wake-Word

States: `IDLE → AWAIT_WAKE → ACTIVE_LISTEN → INACTIVITY_PROMPT_1 (20s) → INACTIVITY_PROMPT_2 (30s) → ENDING (35s) → IDLE`

* Start button → mic permission → **AWAIT_WAKE** with chip: *“Listening for ‘well-bot’…”*.
* Wake phrases: “well-bot”, “well bot”, “hey well-bot”, “hi well-bot” (fuzzy ≥0.85).
* AWAIT_WAKE nudge at 10s: *“Say ‘well-bot’ to begin.”*
* Inactivity prompts:
  20s: *“hey, are you still there?”* → 30s: *“are you still with me?”* → 35s auto-end card: *“It seems like you’re not around, i’ll just go take a break now.”*
* **PTT fallback** when mic unavailable; label **“Hold to speak”**; after first wake via PTT, switch to always-listening.
* Timers reset on any **user activity** (speech start, text, clicks); not on assistant TTS.
* Meditation playback **suspends** inactivity timers; journal overlay has its own 2:00/3:00 rule.

**Tools**

* `session.wake` → start session (card).
* `session.end {reason:"manual"}` → force end (card).
* **Logs**: `wb_session_log {started_at, ended_at, reason_ended, avg_latency_ms, asr_wer_estimate}`.

---

## 3) Safety

* Scope: all user utterances (chat, journal overlay, meditation prompts), EN only (case-insensitive + light stemming).
* Rules: curated phrases (suicidal intent/ideation/self-harm), combos; negation guard. Debounce window **120s**; escalate if severity increases.
* Action: pause current feature, show card *“Support Resources”* for ~5s (OK button), resume.
* Log: `wb_safety_event {session_id, ts, lang, action_taken, user_acknowledged, redacted_phrase, severity}`.

**Tool**

* `safety.check {text, lang, context, session_ts}` → `{ meta.action: "show_support_card"|"none" }`.

---

## 4) Memory / RAG

**Indexed kinds**: `message (user+assistant)`, `journal (final only)`, `todo (title)`, `preference`, `gratitude`.
**Not indexed**: quotes, safety cards, journal overlay transcripts.

* On-write hooks: create/update/delete → (re)embed; journals only when `is_draft=false`.
* Retrieval defaults: `top_k=8`, `min_score=0.35`, **recency boost** `score' = score*(1+0.15*e^{-age_days/14})`, **budget** 1200 tokens.
* Config: `WB_EMBED_MODEL ∈ {miniLM,e5}` gates index+query.

**Tool**

* `memory.search {query, filters:{kinds}, top_k}` → diagnostics payload for router/LLM.

---

## 5) Orchestration & Routing

**Simple Router** with streaming, middlewares:

1. **ASR (stream)**
2. **safety.check** (sync, fast)
3. **FSM gate** (session/wake)
4. **Intent detection** (tool vs small talk)
5. **Small talk topic-cache** (see below)
6. **Optional memory.search** (≤500ms budget; fail-open)
7. **LLM respond** (max 250 toks)
8. **Optional tool call** + **card render**

**Topic Cache (small-talk)**

* Ephemeral session state: `{topic_vector, topic_label, hits, ts_last_update}`
* Similarity threshold **0.78**; **TTL=5m** (evict on tool use or end).
* If on-topic → reuse cached hits; else run `memory.search` and update cache.
* Cap hits cached: **8**.

**Intent set**

* `journal.start`
* `gratitude.add`
* `todo.add|list|complete|delete`
* `quote.get`
* `meditation.play`
* `session.end`
* Disambiguation order: **safety > session > tool > small talk**.

**Latency budgets**

* safety ≤50ms; intent ≤200ms; memory.search ≤500ms; first TTS token ≤1.5s.

---

## 6) Journal (module summary)

* Overlay session (voice-first). Stop controls: **Save & Summarize**, **Save Draft** (default on cancel/inactivity), **Discard**.
* Drafts: `is_draft=true`, summarized entry saved; **not embedded**; dashboard can edit/finalize (flip flag; then embed).
* Interruption → “Activity interrupted” card + TTS.
* Safety inside overlay; 2:00 “Still journaling?” → 3:00 auto **Save Draft**.
* Tables: `wb_journal`, `wb_activity_event`, `wb_embeddings(kind='journal')`.
* Tools: `journal.start`, `journal.stop`, `journal.save`.

---

## 7) To-Do (module summary)

* Chat: **add, list, complete, delete**; dashboard full CRUD.
* Add: split utterance by commas/“and”/newlines; **cap 10**; **truncate >20 words**/item; Title Case; embed on add.
* List (chat): **open items only**, 5 newest + “Show more” (next 10).
* Guardrail: `complete/delete` **only after** a `list` card in current conversation (armed 5 minutes or until list changes).
* Fuzzy match ≥0.75 against **open** items:

  * Single: auto-complete; delete asks confirm (unless from disambiguation).
  * Multiple/low: disambiguation mini-card (top 3).
* Report card always shows **updated open list** (max 5) + footnote action line; TTS mirrors.
* Undo delete 5s. RAG: embed on add/status change.
* Tables: `wb_todo_item`, `wb_activity_event`, `wb_embeddings(kind='todo')`.
* Tools: `todo.add`, `todo.list`, `todo.complete`, `todo.delete`.

---

## 8) Gratitude (module summary)

* Chat: **add** only; dashboard full list + CRUD.
* Entry = full utterance; **Sentence case**; **truncate >100 words** (with “…”); duplicates allowed.
* Safety pre-check; on trigger do not save.
* Success card shows **just the saved entry** + footnote “Saved to your Dashboard.”; embed for RAG.
* Tables: `wb_gratitude_item`, `wb_embeddings(kind='gratitude')`, `wb_activity_event`.
* Tool: `gratitude.add`.

---

## 9) Spiritual Quote (module summary)

* Random-per-request from user’s **religion** with **General** fallback; **3 per session** cap.
* **7-day repeat-avoidance** per user; if none available → info card.
* Reflection: 1 sentence via LLM (no doctrine); quote text verbatim; no attribution; no religion label on card.
* Tables: `wb_quote`, `wb_quote_seen`, `wb_activity_event`.
* Tool: `quote.get`.

---

## 10) Meditation (module summary)

* All videos **3 minutes**; random among `active=true`.
* TTS says intro line; **mute** assistant during playback (video audio only).
* **Cancel** (pause → Yes/No confirm); **Restart** (no confirm).
* Playback suspends session inactivity timers; resume after end/cancel/restart.
* On end/cancel: show report card and ask brief non-numeric check-in (no rating stored).
* Fallback: try other variants on load failure (3s total); else error card.
* Tables: `wb_meditation_video`, `wb_meditation_log`, `wb_activity_event`.
* Tools: `meditation.play`, `meditation.cancel`, `meditation.restart`, `meditation.log`.

---

## 11) Data Schema (new tables, prefix `wb_`)

* `wb_conversation {id, user_id, started_at, ended_at, reason_ended}`
* `wb_message {id, conversation_id, role, text, created_at}` (source for kind='message')
* `wb_journal {id, user_id, title, body, mood int, topics text[], is_draft bool, created_at, updated_at}`
* `wb_gratitude_item {id, user_id, text, created_at}`
* `wb_todo_item {id, user_id, title, status, created_at, completed_at}`
* `wb_meditation_log {id, user_id, video_id, started_at, ended_at, outcome, created_at}`
* `wb_meditation_video {id, uri, label, active bool}`
* `wb_quote {id, category enum, text}`
* `wb_quote_seen {user_id, quote_id, seen_at, pk(user_id,quote_id)}`
* `wb_activity_event {id, user_id, type, ref_id, action, created_at}`
* `wb_embeddings {id, user_id, kind, ref_id, vector, model_tag, created_at}`
* `wb_preferences {user_id pk, language, religion, flags jsonb}`
* `wb_session_log {id, user_id, started_at, ended_at, reason_ended, avg_latency_ms, asr_wer_estimate}`
* `wb_tool_invocation_log {id, session_id, tool, status, duration_ms, error_code?, payload_size}`
* `wb_safety_event {id, session_id, ts, lang, action_taken, user_acknowledged, redacted_phrase, severity}`

**Indexes**: per module docs; pgvector index on `wb_embeddings.vector`.

---

## 12) i18n, Persona, Guardrails

* MVP language **EN**; MS/ZH later (same tone).
* Persona: warm, concise, reflective; avoid therapy labels; **emotion-regulation only**, not outcome advice.
* **Banned**: clinical diagnoses, medical/legal/financial advice, political/religious discussion (beyond quotes), self-harm encouragement.

---

## 13) Config & Secrets (env)

* `WB_EMBED_MODEL=miniLM|e5` (default `miniLM`)
* `WB_RECENCY_ALPHA=0.15`, `WB_RAG_K=8`, `WB_RAG_MIN_SCORE=0.35`
* `WB_TOPIC_SIM_THRESHOLD=0.78`, `WB_TOPIC_TTL_MIN=5`, `WB_TOPIC_MAX_HITS=8`
* `WB_FIRST_TOK_TARGET_S=1.5`, `WB_SAFETY_DEBOUNCE_SEC=120`
* `DEEPGRAM_API_KEY`, `DEEPSEEK_API_KEY`
* `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE`
* `WB_WAKE_PHRASE="well-bot"`

---

## 14) Observability

* Sample **50%** of turns into logs (no PII).
* Track: `{turn_id, latency_ms, intent, used_memory, memory_latency_ms, output_tokens}`.
* Keep logs 30 days.

---

## 15) Acceptance (Global)

* End-to-end pipeline runs with streaming; wake-word → always-listening; PTT fallback.
* Safety interjections pause/resume correctly across contexts.
* Each module behavior matches its LLD; cards render consistently from the standard envelope.
* RAG contributes context with topic-cache; memory.search budget ≤500ms; fail-open is graceful.
* All writes honor RLS by `user_id`; deletions remove embeddings.
* First-token TTS within ~1.5s under normal load.

---

**End of Global LLD (MVP)**
