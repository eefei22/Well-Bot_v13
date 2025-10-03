Perfect—locking in: memory.search budget **≤500 ms** (else fail-open and cache for next turn), small-talk max output **250 tokens**, telemetry sampled at **50%**.

Here’s the **Global LLD — Orchestration & Routing (MVP)**, concise and implementation-focused.

# Well-Bot · Low-Level Design — Global Orchestration & Routing (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Router Architecture

* **Simple Router** with small middlewares (safety, FSM gate, topic-cache, optional memory.search).
* Streaming-first: ASR partials drive early intent; TTS streams when first tokens arrive.

## 2) Per-Turn Pipeline

`ASR (stream) → safety.check (fast sync) → FSM gate → intent detect → if small-talk: topic-cache check → maybe memory.search (≤500ms budget) → LLM respond (max 250 toks) → optional tool call → card render`

* **Fail-open**: if memory.search misses the 500ms budget, answer without it; cache results for next turn.
* **Safety-first**: blocks tool calls; shows support card; resumes afterward.

## 3) Topic Cache (Small-Talk Memory)

* State (ephemeral): `{ topic_vector, topic_label, hits, ts_last_update }`.
* Similarity threshold: **0.78** (cosine).
* TTL: **5 minutes** of inactivity; evict on tool use or session end.
* Update rule: new topic if sim < 0.78 → run memory.search; else reuse cached hits.
* Cap: **8 hits** cached.

## 4) Intent Detection

* Classifier prompt + light regexes for verbs (“add”, “show”, “did”, “delete”, “journal”, “quote”, “meditation”, “bye”).
* Disambiguation order: **safety > session > tool intent > small talk**.
* Exact tool intents: `journal.start`, `gratitude.add`, `todo.add|list|complete|delete`, `quote.get`, `meditation.play`, `session.end`.

## 5) Latency Budgets

* Safety check: ≤ **50 ms**
* Intent detection: ≤ **200 ms**
* memory.search: ≤ **500 ms** (parallel; optional)
* First TTS token: ≤ **1.5 s** target

## 6) Config Flags (env)

* `WB_EMBED_MODEL=miniLM|e5` (default `miniLM`)
* `WB_RECENCY_ALPHA=0.15`, `WB_RAG_K=8`, `WB_RAG_MIN_SCORE=0.35`
* `WB_TOPIC_SIM_THRESHOLD=0.78`, `WB_TOPIC_TTL_MIN=5`, `WB_TOPIC_MAX_HITS=8`
* `WB_FIRST_TOK_TARGET_S=1.5`
* Secrets: `DEEPGRAM_API_KEY`, `DEEPSEEK_API_KEY`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE`
* Other: `WB_WAKE_PHRASE="well-bot"`, `WB_SAFETY_DEBOUNCE_SEC=120`

## 7) Telemetry & Sampling

* Sample **50%** of turns into `wb_tool_invocation_log` plus summary to `wb_session_log`.
* Fields: `{ turn_id, latency_ms, intent, used_memory:boolean, memory_latency_ms, output_tokens }`.
* Redact PII; store snippets only in embeddings, not logs.

## 8) Error Handling & Retries

* Tool call timeouts: **1.5 s** default; single retry on `5xx`.
* If a tool fails → emit **error card** and continue small talk.
* Network hiccups: degrade to text-only (mute TTS) with a banner.

## 9) Acceptance

* Router executes the pipeline per turn with streaming and budgets.
* Small-talk reuses topic cache when on-topic; refreshes on topic change.
* Safety interruptions preempt tool calls and resume correctly.
* Env flags control embeddings model, topic cache, and latency budgets.
* Telemetry recorded at 50% sampling; no PII leakage.
