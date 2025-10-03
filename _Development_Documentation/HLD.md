Here’s the **revised HLD.md** (pure text) aligned to all finalized LLD decisions.

---

# Well-Bot · High-Level Specification (MVP)

*Last updated: 2025-10-02 · Timezone default: Asia/Kuala_Lumpur (UTC+8). Store timestamps in UTC.* 

## 1) Executive Summary

Goal: deliver a **voice-first, MCP-enabled** web application that supports:

* Conversational chat grounded in user memory (RAG).
* Five activities: **Journal (interactive pop-up), Gratitude (single-turn), To-Do (add/list/complete/delete), Spiritual Quote (religion-filtered), Meditation (video with cancel + restart)**.
* Safety interjection on self-harm keywords (support card, auto-resume). 

Success criteria (MVP): all services wired (Deepgram STT/TTS streaming, DeepSeek LLM, Supabase Auth/DB/Storage/pgvector), tools callable via MCP, cards appended to chat, <5s perceived latency, Chrome-first. 

---

## 2) Scope & Guardrails

**In-scope:** chat + 5 activities, memory-grounded responses from user data + curated spiritual quotes (DB).
**Out-of-scope:** medical/legal/financial/trauma advice; religious/political discussion (beyond quotes); home automation; mobile app.
**Safety:** self-harm keyword rules ⇒ pause features, show support card (~5s), then resume chat. 

---

## 3) User & Interaction Model

* Auth: **email+password** (Supabase). Single role, ≤10 concurrent users expected. 
* Wake-word lifecycle (web simulation):

  1. User clicks **Start** → mic permission → hot-mic listens for **“well-bot”** and variants (“well bot”, “hey well-bot”, “hi well-bot”).
  2. On detection: **Always-listening** state until termination.
  3. Termination: user intent (“bye”, “talk later”), or inactivity prompts at **20s** “hey, are you still there?”, **30s** “are you still with me?”, then auto-end at **35s** with end card: “It seems like you’re not around, i’ll just go take a break now.” Also play a 10s nudge in AWAIT_WAKE: “Say ‘well-bot’ to begin.” (Supersedes older copy.) 
* Input/Output: **Voice primary**, **typed fallback**; TTS responses (no barge-in), except **Meditation** supports confirm-to-cancel and restart. 
* Activity overlays:

  * **Journal:** pop-up session; only **final entry** is persisted; summarized paragraph appended as card.
  * **Gratitude/To-Do/Quote/Meditation:** actions produce **report cards** appended to chat. 

---

## 4) System Context & Architecture

* **Client (Chrome)**: React+Vite app, MCP **client**; left sidebar (Chat, Dashboard, Settings/Logout), middle = past conversations, right = active chat.
* **Speech**: Deepgram **streaming STT** (partials+punctuation), **streaming TTS** (neutral voice; speed ~1.0x).
* **LLM**: DeepSeek (chat/tool use). **No “reasoning” mode**.
* **Data**: Supabase (Auth/Postgres/Storage), **pgvector** for embeddings.
* **RAG**: index past chats (user+assistant), final journals, to-dos, **gratitude**, preferences.
* **Embeddings**: Default **all-MiniLM-L6-v2** (EN) and alt **e5-small-v2** (multilingual), gated at index+query.
* **Safety**: keyword rule checker (MCP tool) + support card; logging to SafetyEvent.
* **Extensibility**: each activity = distinct MCP tool with strict JSON I/O. 

---

## 5) MCP Tooling (Contracts)

### 5.1 Tool Catalogue (MVP)

* `session.wake`, `session.end`
* `safety.check`
* `memory.search`
* `journal.start`, `journal.stop`, `journal.save`
* `gratitude.add`  *(removed `gratitude.list` in chat)*
* `todo.add`, `todo.list`, `todo.complete`, **`todo.delete`**
* `quote.get` (religion-filtered; “General” fallback if unset)
* `meditation.play`, `meditation.cancel`, **`meditation.restart`**, `meditation.log`
* `activityevent.log` (as utility)
  (Updates supersede earlier catalogue.) 

### 5.2 Standard Request/Response Envelopes

**Request (global fields)**: `{ trace_id, user_id, conversation_id, session_id, args, ts_utc }`
**Response (success)** must include `"status": "ok"` and the card envelope; on error, `"status": "error"` and `type:"error_card"`. (Adds `status` to the earlier envelope.) 

### 5.3 Error Card (uniform)

Shape retained; all errors set `"status":"error"` and `meta.error_code`. 

---

## 6) Data & Storage (High-Level)

**Prefix all new tables with `wb_`**. Store timestamps as UTC. (Revises prior list.)

* `wb_conversation {id, user_id, started_at, ended_at, reason_ended}`
* `wb_message {id, conversation_id, role("user"|"assistant"), text, created_at}`
* `wb_journal {id, user_id, title, body, mood, topics, **is_draft bool**, created_at, **updated_at**}`
* `wb_gratitude_item {id, user_id, text, created_at}`
* `wb_todo_item {id, user_id, title, status("open"|"done"), created_at, completed_at}`
* `wb_meditation_log {id, user_id, video_id, started_at, ended_at, **outcome only (no user_calm)** }`
* **`wb_meditation_video {id, uri, label, active bool}`**
* **`wb_quote {id, category enum('islamic','buddhist','christian','hindu','general'), text}`**, **`wb_quote_seen {user_id, quote_id, seen_at, pk(user_id,quote_id)}`**
* `wb_activity_event {id, user_id, type, ref_id, action, created_at}`
* `wb_preferences {user_id pk, language, religion}`
* `wb_embeddings {id, user_id, kind("message"|"journal"|"todo"|"preference"**|"gratitude"**), ref_id, vector(pgvector), model_tag("miniLM"|"e5"), created_at}`
* `wb_session_log {id, user_id, started_at, ended_at, reason_ended, avg_latency_ms, asr_wer_estimate}`
* `wb_tool_invocation_log {id, session_id, tool, status, duration_ms, error_code?, payload_size}`
* `wb_safety_event {id, session_id, ts, lang, action_taken, user_acknowledged, redacted_phrase, **severity**}`
  Retention: logs 30 days. (Supersedes prior HLD fields.) 

---

## 7) RAG & Embeddings

* **Index on write**: when message/journal(final only)/todo(add & status change)/**gratitude**/preference created or updated; remove vectors on delete.
* **Query**: top-k semantic search (k configurable), with recency boost; budgeted snippets for grounding.
* **Model selection**: config flag chooses **miniLM** (EN) or **e5** (multilingual) for both **index and query**.
* **Quotes**: not indexed (fetched from DB; no attribution). (Expands prior scope to include gratitude; journals only when not draft.) 

---

## 8) Key Flows (Text Only)

### 8.1 Chat + Card Append

1. User says “well-bot …” → `session.wake` → STT streaming on.
2. Router detects intent; optional `memory.search` (topic cache, ≤500 ms budget).
3. If a tool runs, it returns a **card** → append to chat (right panel). 

### 8.2 Journal (Pop-Up)

1. “start a journal” → `journal.start` → overlay opens.
2. Pop-up agent conducts multi-turn.
3. End via intent/button → `journal.stop` → LLM summarizes → `journal.save`.
4. Card appended; **only final entry persisted** (drafts allowed but not embedded). 

### 8.3 To-Do

1. “show my to-do list” → `todo.list` → **open-items list card** (5 newest; “Show more”).
2. “I did X” / delete X → guardrail requires a recent list shown (armed ~5 min); fuzzy ≥0.75; on success show the **updated open list** (no before/after delta). (Replaces earlier “delta card” language.) 

### 8.4 Gratitude

“add a gratitude …” → `gratitude.add` → **single entry card** (sentence case; truncate at 100 words with “…”; safety pre-check). (Chat list removed; dashboard lists all.) 

### 8.5 Spiritual Quote

“give me a quote” → `quote.get` (religion or General fallback) → **quote card** + 1-sentence reflection; **3 per session cap**; **7-day repeat avoidance**. (Adds caps over prior text.) 

### 8.6 Meditation

“start a meditation” → `meditation.play` (random **3-min** video; TTS intro then muted during playback) → cancel confirms (Yes/No) or **restart** (no confirm) → on end/cancel: `meditation.log` (no calm rating) → completion/canceled card → brief check-in. (Adds restart + audio policy.) 

### 8.7 Safety

`safety.check` on each user utterance; on hit → **support card** (generic copy) ~5s; log SafetyEvent (masked snippet + severity); auto-resume chat/overlay. (Replaces specific hotlines for MVP.) 

---

## 9) Assistant Persona & UX Writing

Tone: warm, concise, user-centric, reflective listening, emotion regulation (not problem-solving).
**Banned phrases:** no diagnoses, medical/legal/financial advice, political/religious debate, or encouragement of self-harm.
**Decline templates:** religion/politics and high-risk advice responses as short declines. 

---

## 10) Non-Functional Requirements

* **Latency**: perceived < **5s** with streaming STT/TTS; first token target ≤1.5 s; memory.search ≤500 ms (fail-open).
* **Availability**: best-effort (school project); graceful error cards.
* **Scalability**: ≤10 concurrent users; minimal cost. 

---

## 11) i18n, Time & Locale

MVP language: **English**; Malay/Chinese later, same tone.
Store timestamps in **UTC**; display local time (Asia/Kuala_Lumpur). 

---

## 12) Security & Privacy

* Supabase Auth (email+password).
* First-run **consent banner** (“I understand”) describing stored data types and crisis guidance.
* Stored categories: user/system messages, final journals, gratitude items, to-dos, preferences, basic metadata.
* Deletes: user-initiated from Dashboard; no export in MVP. 

---

## 13) Environments & Deployment

* **Chrome-first** web client.
* Supabase project reuse; create new `wb_*` tables; **migrate** old data (copy/reshape) and keep originals.
* Supabase Storage: host meditation videos (3 variants, random selection).
* Config flags: embeddings model (`miniLM|e5`), k, thresholds, wake-word phrase, topic-cache thresholds (sim=0.78, TTL=5m). 

---

## 14) Orchestration & Routing (Global)

* **Simple Router** with streaming middlewares: `ASR → safety.check → FSM gate → intent detect → (small-talk) topic cache → optional memory.search → LLM respond (≤250 toks) → tool call → card`.
* **Topic cache**: cosine sim threshold **0.78**, TTL **5 min**, cache up to **8** hits; memory.search budget **≤500 ms** (fail-open).
* **Telemetry**: sample **50%** of turns into logs; redact PII. (Adds to original architecture narrative.) 

---

## 15) Acceptance Criteria (MVP Demo)

1. Wake-word start → continuous STT → normal termination; inactivity prompts (20/30s) and **warm** auto-end card at 35s. 
2. Journal pop-up conducts multi-turn; on stop, saved entry appears as **report card**; only final entry persisted. Drafts possible; only finalized entries embedded. 
3. Gratitude add → **single entry card** (sentence case; ≤100 words; safety pre-check). (Replaces “list shows cumulative” behavior.) 
4. To-Do add/list/complete/**delete** → **updated open list** card (max 5, newest first; “Show more”); guardrail: complete/delete only after a recent list shown. (Replaces “before/after delta”.) 
5. Spiritual quote returns DB entry filtered by religion (or General), includes 1-line reflection; **3 per session cap**; **7-day repeat avoidance**. 
6. Meditation plays video (3-min, random); **cancel** (confirm) and **restart** (no confirm); completion/cancel logged; assistant gives brief non-numeric check-in. 
7. Safety keyword triggers **support card** (generic copy), logs SafetyEvent with masked snippet+severity, resumes chat/overlay. 
8. RAG retrieves from user messages, journals(final), to-dos, **gratitude** (not quotes). 
9. All tools return **standard JSON** with `"status"`; error scenarios render **error cards**. 
10. Metrics available (low priority UI): WER estimate, median latency, safety event counts; logs retained 30 days. 

---

**End of High-Level Specification (MVP)**
