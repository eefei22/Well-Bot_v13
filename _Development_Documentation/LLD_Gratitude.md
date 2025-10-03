# Well-Bot · Low-Level Design — Gratitude Feature (MVP)

*Last updated: 2025-10-02 · Store timestamps in UTC (UI: Asia/Kuala_Lumpur).*

## 1) Scope

Chat: **add** only.
Dashboard: full list + CRUD.
After add, show **single-entry card** (the just-saved item) with footnote “Saved to your Dashboard.”
Interruptions append the standard **“Activity interrupted”** card and continue chat.

## 2) Data Model

**wb_gratitude_item**
`{ id uuid pk, user_id uuid fk, text text, created_at timestamptz }`
Index: `(user_id, created_at desc)`

**wb_embeddings** (gratitude items)
`{ id uuid pk, user_id uuid, kind 'gratitude', ref_id uuid, vector, model_tag 'miniLM'|'e5', created_at }`

## 3) Normalization & Limits

* Input: take the **entire utterance** as one entry (no splitting).
* Normalize: `trim → sentence case` (capitalize first letter; preserve user punctuation; no emoji filtering).
* Length: **max 100 words**; if exceeded → **truncate to 100 words** and append `…` (visible + TTS notice).
* Duplicates: **allowed** (same text on different days).

## 4) Safety

* Run `safety.check` **before save**. If triggered → show support card, **do not save**, resume chat.

## 5) MCP Tool (Contract)

Global envelopes per project standard.

### `gratitude.add`

**Args**

```json
{ "text": "string" }
```

**Behavior**

1. Safety check; abort on trigger.
2. Normalize to sentence case; truncate >100 words.
3. Insert row in `wb_gratitude_item`.
4. Embed stored text to `wb_embeddings(kind='gratitude')`.
5. Create `wb_activity_event(type='gratitude', action='created', ref_id=item_id)`.

**Response (success)**

```json
{
  "status": "ok",
  "type": "card",
  "title": "Gratitude Saved",
  "body": "<final stored text (possibly truncated)>",
  "meta": { "kind": "gratitude" },
  "persisted_ids": { "primary_id": "<item_id>" },
  "diagnostics": { "tool": "gratitude.add", "duration_ms": 0 }
}
```

**Errors**

* `VALIDATION_ERROR` (empty after trim)
* `SAFETY_BLOCKED`
* `DB_WRITE_FAILED`

## 6) Cards & UX

* **Success card**: as above + footnote in small text: “Saved to your Dashboard.”
* **Too long notice**: visible subtext “Entry was long—shortened to 100 words.”
  TTS: “I’ve shortened that a little and saved it.”
* **Activity interrupted**: standard project copy.

## 7) Logging

* `wb_tool_invocation_log`: record `gratitude.add` (status, duration_ms, error_code?, payload_size).
* `wb_activity_event`: `('gratitude','created')`.
* `wb_safety_event`: when blocked by safety.
  Retention: 30 days.

## 8) Acceptance

* Adds one entry per call; no splitting; sentence case applied.
* Truncates >100 words with “…”, shows visual+audible notice.
* Safety hit prevents save and shows support card.
* Success returns “Gratitude Saved” card with the stored text and persisted id.
* Entry embedded for RAG.
* Interruption shows standard interruption card and resumes chat.
