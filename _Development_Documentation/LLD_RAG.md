# Well-Bot · Low-Level Design — Memory / RAG (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Scope

Index the following per-user sources for retrieval in chat:

* **Messages**: user + assistant text (one chunk per message; exclude system prompts).
* **Journals**: **finalized** entries only (drafts excluded).
* **To-Dos**: each item (title only).
* **Preferences**: compact doc (language, religion, misc flags).
* **Gratitude**: each item (final text).
  Exclude: spiritual quotes, safety/support cards, journal overlay transcripts.

## 2) Embeddings & Config

* Models: **all-MiniLM-L6-v2** (default EN), **e5-small-v2** (multilingual alt).
* Config flag `WB_EMBED_MODEL ∈ {"miniLM","e5"}` gates both **index** and **query**.
* Vector dim per model; stored in `pgvector`.
* Re-embed on edits (journals final only; to-dos on status change; messages immutable).

## 3) Data Schema

**wb_embeddings**
`{ id uuid pk, user_id uuid, kind 'message'|'journal'|'todo'|'preference'|'gratitude', ref_id uuid, vector vector(dim), model_tag 'miniLM'|'e5', created_at timestamptz }`
Indexes: `(user_id, kind, ref_id)`, HNSW/IVFFlat on `vector` (per pgvector build).

**wb_preferences**
`{ user_id uuid pk, language text default 'en', religion text null, flags jsonb default '{}' }`

**wb_message** (already in project) provides source rows for kind='message'.

## 4) Indexing (On-Write Hooks)

* **Message**: on insert → embed content (`role in ('user','assistant')`).
* **Journal**: on finalize (`is_draft=false`) or on edit of finalized → (re)embed `title + "\n\n" + body`.
* **To-Do**: on add and on status change → embed `title` (keep even when `done`).
* **Preferences**: on upsert → embed normalized small blob (e.g., `language=en; religion=general`).
* **Delete**: remove embedding rows for the deleted `ref_id` (journal/todo/message/gratitude).
* **Gratitude**: on save → embed final stored text.

Normalization before embed: strip HTML, collapse whitespace; keep case/punctuation.

## 5) Retrieval Policy (Defaults)

* **Top-k**: 8, **min score**: 0.35 (discard below).
* **Filters** (always): `user_id`.
* **Kind biasing** (optional per intent):

  * planning → prefer `todo`, then recent `message`.
  * journaling follow-ups → prefer recent `journal`, `gratitude`.
* **Recency boost**: `score' = score * (1 + 0.15 * exp(-age_days/14))`.
* **Budget**: up to **1200 tokens** total context; order by boosted score; stop when budget reached.
* **Return**: list of `{kind, ref_id, snippet, score, created_at}`.

## 6) MCP Tool — `memory.search`

**Args**

```json
{
  "query": "string",
  "filters": { "kinds": ["message","journal","todo","preference","gratitude"] },
  "top_k": 8
}
```

**Behavior**

1. Resolve embedding model per `WB_EMBED_MODEL`.
2. Embed the `query`; vector search with filters; apply recency boost; cut at score ≥0.35; cap at 1200 tokens of snippets.
3. Return a **card** for diagnostics **or** a pure payload (no card) depending on caller:

   * In normal chat, return **payload-only** in `diagnostics` and let the LLM decide grounding.
   * For debug, can return a developer card (behind a flag).

**Response (payload-focused success)**

```json
{
  "status": "ok",
  "type": "card",
  "title": "Memory hits",
  "body": "Top results attached.",
  "meta": { "kind": "info" },
  "persisted_ids": {},
  "diagnostics": {
    "tool": "memory.search",
    "duration_ms": 0,
    "results": [
      { "kind": "todo", "ref_id": "...", "snippet": "Buy cables for lab.", "score": 0.82, "created_at": "..." },
      { "kind": "journal", "ref_id": "...", "snippet": "I felt calmer after...", "score": 0.78, "created_at": "..." }
    ]
  }
}
```

**Errors**

* `EMBEDDING_MODEL_UNAVAILABLE`, `VECTOR_SEARCH_FAILED`, `DB_READ_FAILED`.

## 7) Snippet Assembly

Per kind:

* **message**: the message text; include `role` in snippet header for the LLM (e.g., “(user)” or “(assistant)”).
* **journal**: title + first 200 chars of body.
* **todo**: title only.
* **preference**: minimal key-values (e.g., `religion=general`).
* **gratitude**: first 200 chars.

## 8) Security & Privacy

* **Row Level Security (RLS)**: all reads/writes filtered by `user_id`.
* **No cross-user recall**.
* Quotes are not indexed; journal overlay transcripts are not stored.
* Respect deletions: remove embeddings on delete; downstream caches invalidated.

## 9) Quality Controls

* **WER-aware fallback** (optional later): if prompt mentions misheard content, bias toward **messages from the last 24h**.
* **Dedup**: if multiple hits share same `ref_id`, keep the highest score.
* **Diversity** (optional later): cap max 5 results per kind to avoid crowding.

## 10) Logging

* **wb_tool_invocation_log**: record `memory.search` with `status`, `duration_ms`, `top_k_effective`, `filters`.
* **wb_activity_event**: none (search-only).
  Retention: 30 days.

## 11) Acceptance

* Indexes created on-write for all approved kinds; deletions clean up vectors.
* Query returns up to 8 boosted, filtered hits, within 1200-token budget.
* Journals: only finalized entries are retrievable; draft edits not embedded.
* To-Dos and Gratitude embedded as specified for context recall.
* Model choice switchable via config; both index and query respect it.
* RLS prevents cross-user leakage.
