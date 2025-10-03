# Well-Bot · Low-Level Design — To-Do Feature (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Scope

Chat-side operations: **add, list, complete, delete**.
Dashboard: full CRUD, bulk “delete completed”.
Duplicates allowed; **delete** removes **one** matching entry per call.

## 2) Data Model

**wb_todo_item**
`{ id uuid pk, user_id uuid fk, title text, status "open"|"done", created_at timestamptz, completed_at timestamptz null }`
Indexes: `(user_id, status, created_at desc)`, `(user_id, title)`.

**wb_activity_event**
`{ id uuid pk, user_id uuid fk, type 'todo', ref_id uuid, action 'added'|'completed'|'deleted', created_at timestamptz }`

**wb_embeddings** (to-do items)
`{ id uuid pk, user_id uuid, kind 'todo', ref_id uuid, vector, model_tag 'miniLM'|'e5', created_at }`
Embed on **add** and on **status change**.

## 3) Normalization & Limits

* **Normalization (on add)**: `trim → collapse spaces → Title Case` (preserve acronyms as-is).
* **Per-item length**: **max 20 words**. If exceeded → **truncate to 20 words** and append `…` (visible+audible notice).
* **Multi-add parsing**: split a single utterance by **commas, semicolons, newlines, and the word “and”**.
* **Add cap per request**: **max 10 items**. If overflow → accept first 10; emit error line for skipped remainder (with TTS).

## 4) Context Guardrail (action arming)

`complete`/`delete` are allowed **only after a `list` card has been shown** in the **current conversation**.
Arming expires after **5 minutes** or when the open-list changes (add/complete/delete).
If unarmed → return info card: “I need to show your list first—say ‘show my to-do list’.”

## 5) Fuzzy Match Policy

* Candidate set: **open** items only (for `complete`/`delete`).
* Similarity: token-based cosine / Jaro-Winkler hybrid (impl detail) → **threshold ≥ 0.75**.
* **One match ≥ 0.75** → auto action (no extra confirm for complete; delete still confirms, see §9).
* **Multiple ≥ 0.75** or **all < 0.75** → disambiguation mini-card (top 3 by score, tie-break = newest first).

## 6) MCP Tools (Contracts)

Global request/response envelopes per project standard.

### 6.1 `todo.add`

**Args**

```json
{ "titles": ["string", "..."], "return_list_after": true }
```

**Behavior**

* Normalize & enforce limits (split, cap 10, truncate >20 words).
* Insert rows (status="open"); create `wb_activity_event('added')`.
* Embed each item.
  **Response**: `type:"card"`, **mini list** of current **open** items (max 5, newest first) + “Show more”.

### 6.2 `todo.list`

**Args**

```json
{ "status": "open", "limit": 5, "cursor": null }
```

**Behavior**

* Fetch **open** items, newest-first.
* Return **list card** with up to `limit` items; include `cursor` if more.
  **Pagination in chat**: “Show more” → `limit:10` per page append.

### 6.3 `todo.complete`

**Args**

```json
{ "title": "string", "return_list_after": true }
```

**Behavior**

* Require **armed** state (see §4).
* Fuzzy match over **open** items.

  * Single ≥0.75 → mark that **one** item `status="done"`, set `completed_at=now()`.
  * Multiple/low → disambiguation mini-card (user selects → re-call with `id`).
* Create `wb_activity_event('completed')`.
* Re-embed (status change).
  **Response**: **updated open-list card** (max 5) with footnote “Marked ‘X’ as done.”
  **TTS**: “Marked ‘X’ as done.”

### 6.4 `todo.delete`

**Args**

```json
{ "title": "string", "return_list_after": true }
```

**Behavior**

* Require **armed** state.
* Fuzzy match (open items).

  * Single ≥0.75 → **confirm** delete (“Delete ‘X’?” Yes/No, 5s window).
  * Multiple/low → disambiguation mini-card (then confirm on selected).
* On yes: delete that **one** row; event `('deleted')`; remove embedding.
  **Response**: **updated open-list card** (max 5) with footnote “Deleted ‘X’.”
  **TTS**: “Deleted ‘X’. I’ve updated your list.”
  **Undo**: 5s inline “Undo” → restore row (same id, same created_at), re-embed.

### 6.5 Disambiguation mini-card (reply target)

* Shows up to **3** candidates `{ id, title, created_at }`.
* User picks → client calls `todo.complete` or `todo.delete` with `{ id }`.

## 7) Cards & Rendering

* **Primary report card** after any successful add/complete/delete: **mini open-list (max 5, newest first)**.
* Footnote line shows the **action summary** (“Added: … / Marked done: … / Deleted: …”).
* “Show more” loads **next 10** items and **expands** the same card.
* **Unsupported chat commands** (e.g., “show completed”): info card + TTS

  > “I’m unable to do that in chat; you can head to the Dashboard to view the full list.”

## 8) Error & Info Feedback (visible + audible)

* **Too long / overflow**:
  Card: “Some entries were too long or too many. I kept the first items and shortened long ones.”
  TTS: “That to-do entry was a little too long—I've shortened it.”
* **Unarmed action**:
  Card: “Let’s show your list first.”
  TTS: “I need to show your list first.”
* **No match**:
  Card: “Not sure which item you meant. Please pick one.” (with suggestions if any)
  TTS: “I’m not sure which item you meant.”

## 9) Confirmations

* **Complete (single confident match)**: no extra confirm; immediate update + TTS.
* **Delete**: always confirm unless action followed an explicit disambiguation pick.
  Prompt: “Delete ‘{title}’?” → buttons Yes/No (5s).
  If timeout → No.

## 10) Activity Interruption

If the to-do action flow is interrupted (e.g., mic loss), append **“Activity interrupted”** card (standard copy) and continue the chat.

## 11) RAG Integration

Embed to-dos so the assistant can recall mundane plans.

* Index on **add** and **status change**.
* Query-time filters can bias toward **open** items for recall prompts.

## 12) Logging

* **wb_tool_invocation_log**: all `todo.*` with `status`, `duration_ms`, `error_code?`, `payload_size`.
* **wb_activity_event**: `added|completed|deleted` per item.
  Retention: 30 days.

## 13) Acceptance (feature)

* Add supports multi-item split, cap 10, truncate >20 words, normalized Title Case.
* List returns open items (5) with cursor; “Show more” appends next 10.
* Complete/Delete require armed list view; fuzzy ≥0.75; disambiguation & confirms as specified.
* Report card always shows updated open-list + footnote; TTS mirrors action.
* Undo delete (5s) works.
* RAG embeddings created/updated accordingly.
* Error/info feedback appears and is spoken.
