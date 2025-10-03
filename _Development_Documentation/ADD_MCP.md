Got it—here’s a tight **fastMCP Addendum (Python)** with only what you need to wire it in and the few global-rule tweaks.

# fastMCP Addendum (Python)

## 0) What changes (summary)

* Add a **single Python fastMCP server** exposing all tools with our **global envelopes**.
* **Auth** at server edge (Supabase JWT or static key).
* Uniform **error→error_card** mapping middleware.
* **No client changes** (same MCP tool names & args).
* Minor global rules at the end.

---

## 1) Env & config

Add to `.env` (server side):

```
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
FASTMCP_AUTH_MODE=supabase|static
FASTMCP_AUTH_KEY=dev-secret   # if AUTH_MODE=static
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE=...
DEEPGRAM_API_KEY=...
DEEPSEEK_API_KEY=...
WB_EMBED_MODEL=miniLM         # or e5
WB_TOPIC_SIM_THRESHOLD=0.78
WB_TOPIC_TTL_MIN=5
WB_SAFETY_DEBOUNCE_SEC=120
```

---

## 2) Project layout (server)

```
backend/mcp_tools/
  envelopes.py           # MCPRequest/MCPResponse, ok_card/error_card
  middleware.py          # safety, timeouts, logging
  tools/
    journal.py
    todo.py
    gratitude.py
    quote.py
    meditation.py
    memory.py
    safety.py
    session.py
    activityevent.py
```

---

## 3) Envelopes (global)

```python
# envelopes.py
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class MCPRequest(BaseModel):
    trace_id: str
    user_id: str
    conversation_id: str
    session_id: str
    args: Dict[str, Any] = Field(default_factory=dict)
    ts_utc: str

class Card(BaseModel):
    status: str                    # "ok"|"error"
    type: str                      # "card"|"overlay_control"|"error_card"
    title: str
    body: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    persisted_ids: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
```

---

## 4) Bootstrap & middleware

```python
# app.py
from fastmcp import MCPApp  # if your lib exposes this; otherwise your server framework
from middleware import auth_mw, envelope_mw, error_mw, timing_mw
from tools import journal, todo, gratitude, quote, meditation, memory, safety, session, activityevent

app = MCPApp()

# Global middlewares (order matters)
app.use(timing_mw)     # start/stop timers, add duration_ms
app.use(auth_mw)       # validate Supabase JWT or static key; attach user_id
app.use(envelope_mw)   # validate MCPRequest; ensure response is Card shape
app.use(error_mw)      # map exceptions -> error_card consistently

# Tool registration (names must match HLD/LLD)
app.tool("journal.start")(journal.start)
app.tool("journal.stop")(journal.stop)
app.tool("journal.save")(journal.save)

app.tool("gratitude.add")(gratitude.add)

app.tool("todo.add")(todo.add)
app.tool("todo.list")(todo.list)
app.tool("todo.complete")(todo.complete)
app.tool("todo.delete")(todo.delete)

app.tool("quote.get")(quote.get)

app.tool("meditation.play")(meditation.play)
app.tool("meditation.cancel")(meditation.cancel)
app.tool("meditation.restart")(meditation.restart)
app.tool("meditation.log")(meditation.log)

app.tool("memory.search")(memory.search)
app.tool("safety.check")(safety.check)
app.tool("session.wake")(session.wake)
app.tool("session.end")(session.end)
app.tool("activityevent.log")(activityevent.log)

if __name__ == "__main__":
    app.run(host=os.getenv("FASTMCP_HOST","0.0.0.0"),
            port=int(os.getenv("FASTMCP_PORT","8000")))
```

**Auth middleware (sketch):**

```python
# middleware.py
import os, jwt
from envelopes import MCPRequest, Card

def auth_mw(handler):
    async def _mw(ctx, req: dict):
        mode = os.getenv("FASTMCP_AUTH_MODE","static")
        token = ctx.headers.get("authorization","").replace("Bearer ","")
        if mode=="static":
            if token != os.getenv("FASTMCP_AUTH_KEY"):
                return Card(status="error", type="error_card", title="Unauthorized",
                            body="Invalid token", meta={"tool":ctx.tool}, error_code="UNAUTHORIZED")
        else:
            # Supabase JWT verify (signature only or via /auth/v1/user)
            try:
                jwt.decode(token, options={"verify_signature": False})  # or verify with JWKs
            except Exception:
                return Card(status="error", type="error_card", title="Unauthorized",
                            body="Invalid JWT", meta={"tool":ctx.tool}, error_code="UNAUTHORIZED")
        return await handler(ctx, req)
    return _mw
```

**Envelope guard & error mapper (sketch):**

```python
def envelope_mw(handler):
    async def _mw(ctx, req):
        parsed = MCPRequest(**req)  # raises on bad shape
        ctx.req = parsed
        res = await handler(ctx, parsed)
        assert isinstance(res, Card), "Tool must return Card"
        # inject timing + tool name
        res.diagnostics.setdefault("tool", ctx.tool)
        return res
    return _mw

def error_mw(handler):
    async def _mw(ctx, req):
        try:
            return await handler(ctx, req)
        except ValueError as e:
            return Card(status="error", type="error_card", title="Validation error",
                        body=str(e), meta={"tool":ctx.tool}, error_code="VALIDATION_ERROR")
        except Exception as e:
            return Card(status="error", type="error_card", title="Action failed",
                        body="Unexpected error", meta={"tool":ctx.tool}, error_code="UNEXPECTED")
    return _mw
```

---

## 5) Tool handler pattern (example)

```python
# tools/todo.py
from envelopes import Card
from lib.supabase import db
from lib.embeddings import embed_todo_title
from lib.utils import normalize_titlecase, split_multi_add   # if needed

async def add(ctx, req):
    titles = req.args.get("titles", [])
    return_list_after = bool(req.args.get("return_list_after", True))
    # normalize + truncate 20 words; cap 10 items
    items = normalize_titlecase(titles)[:10]
    items = [truncate_words(x, 20) for x in items]
    ids = []
    for t in items:
        row = await db.todo_add(req.user_id, t)
        await embed_todo_title(req.user_id, row["id"], t)
        ids.append(row["id"])
    # fetch updated open list (max 5)
    lst = await db.todo_list_open(req.user_id, limit=5) if return_list_after else []
    body = "\n".join([f"• {r['title']}" for r in lst]) if lst else "Your list is empty."
    return Card(
        status="ok", type="card", title="To-Do (updated)",
        body=body, meta={"kind":"todo"},
        persisted_ids={"primary_id": ids[0] if ids else None},
        diagnostics={"duration_ms": ctx.timing()}
    )
```

Follow the same pattern for each tool, enforcing the LLD rules (e.g., gratitude truncation to 100 words, quote caps, journal draft vs final, etc.).

---

## 6) Streaming, budgets, and topic cache

* **Streaming** remains client-side with Deepgram + DeepSeek; fastMCP handlers are short-lived RPCs.
* Keep our budgets: safety ≤50 ms; intent ≤200 ms; memory.search ≤500 ms (server returns quickly; fail-open if slower).
* Topic-cache stays **in the web client** (session memory). No server change needed.

---

## 7) Logging

* In `timing_mw`, compute `duration_ms` and inject into `Card.diagnostics`.
* Also write **wb_tool_invocation_log** from fastMCP (server-role Supabase key) with:
  `{jawbone_id?, session_id, tool, status, duration_ms, error_code?, payload_size}`.
* Respect 50% sampling.

---

## 8) Deployment

* Run fastMCP alongside the web app (same container or separate tiny service).
* Expose on `FASTMCP_PORT` (internal). Web client points MCP transport to this URL and includes the **Bearer** token per request.

---

## 9) Minor **global-rule** updates

* **Auth rule:** client must include `Authorization: Bearer <token>` in every MCP call.
* **Response rule:** every handler **must** return a `Card` with `status` set; errors **must** go through `error_mw`.
* **Safety-first:** client still calls `safety.check` before routing; optionally, you can **also** wrap handlers with a tiny pre-check in the server if you want belt-and-braces (not required).
* **Idempotency:** respect `trace_id` in handlers where specified (e.g., `journal.save`)—use a small server-side cache/table to dedupe.

---

## 10) Quick checklist (to wire fastMCP)

* [ ] Add envs & secrets.
* [ ] Create `services/mcp` with the files above.
* [ ] Implement auth/envelope/error middlewares.
* [ ] Port each tool’s handler per LLD (same names/args).
* [ ] Point the React MCP client to the fastMCP URL, include `Authorization`.
* [ ] Smoke-test with 2–3 tools (todo.add, gratitude.add, quote.get).
* [ ] Add health endpoint/tool (optional) for CI.

That’s it—drop these in and you’ll have the tool server up with minimal churn. If you want, I can sketch a tiny `docker-compose.yml` next to run web + fastMCP + a local supabase instance for dev.



