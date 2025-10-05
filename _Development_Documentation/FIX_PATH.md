Great—your bundle nails the culprits. Here’s a tight fix plan you can apply immediately.

# Fix order (do these now)

## 1) Activate venv & install deps (so `openai` exists where uvicorn runs)

```powershell
# from repo root
.\.venv\Scripts\Activate.ps1
python -V
python -m pip install "openai>=1.45.0" "uvicorn[standard]" watchfiles
```

## 2) Make your folders real Python packages

Create empty `__init__.py` files (four you’re missing):

```powershell
ni src\__init__.py -ItemType File
ni src\backend\__init__.py -ItemType File
ni src\backend\services\__init__.py -ItemType File
ni src\backend\core\__init__.py -ItemType File
```

## 3) Switch all imports to **absolute** (match your `src` layout)

**`src/backend/api/main.py`**

```python
# OLD (wrong)
from routes.health import router as health_router
from routes.speech import router as speech_router
from routes.llm import router as llm_router

# NEW (absolute)
from src.backend.api.routes.health import router as health_router
from src.backend.api.routes.speech import router as speech_router
from src.backend.api.routes.llm import router as llm_router
```

**`src/backend/api/routes/llm.py`**

```python
# OLD
from services.deepseek import chat_completion
from core.intent_detector import detect_intent
from mcp_tools.tools.safety_tool import check as safety_check
from mcp_tools.envelopes import Card, ok_card, error_card, Diagnostics

# NEW
from src.backend.services.deepseek import chat_completion
from src.backend.core.intent_detector import detect_intent
from src.backend.mcp_tools.tools.safety_tool import check as safety_check
from src.backend.mcp_tools.envelopes import Card, ok_card, error_card, Diagnostics
```

(adjust the `src.backend.mcp_tools...` path to your actual location—keep the `src.` prefix)

## 4) Ensure Python can see `src/` (set PYTHONPATH for this shell)

```powershell
$env:PYTHONPATH = (Get-Location).Path
```

## 5) Start uvicorn **via the venv Python** (so the reloader inherits the venv)

```powershell
python -m uvicorn src.backend.api.main:app --reload --port 8000
```

# Quick verification

## A) Check routes are mounted

Open: `http://127.0.0.1:8000/docs`
You should see `/llm/chat:turn` (or whatever you used).
If you don’t, add this temporary dump at the bottom of `main.py` (after `include_router` calls) and restart:

```python
for r in app.router.routes:
    try:
        print("ROUTE", r.methods, r.path)
    except Exception as e:
        print("ROUTE_PRINT_ERR", e)
```

## B) Probe the endpoint directly

Depending on your path (colon vs slash):

```powershell
# colon version
curl.exe -sS -X POST "http://127.0.0.1:8000/llm/chat:turn" -H "Content-Type: application/json" -d "{""text"":""hello"",""user_id"":""u1""}" -i

# or, if you changed to slash (recommended to avoid odd proxies):
curl.exe -sS -X POST "http://127.0.0.1:8000/llm/chat/turn" -H "Content-Type: application/json" -d "{""text"":""hello"",""user_id"":""u1""}" -i
```

* **422** means the route exists (great) — then fix the request schema next.
* **404** still → the router isn’t included or the prefix differs. Double-check:

  ```python
  app.include_router(llm_router, prefix="/llm", tags=["llm"])
  ```

# Common foot-guns to avoid

* Running `uvicorn` without the venv → child reloader can’t see `openai`.
* Relative imports (`from routes...`) when you’re in a `src/` layout.
* Missing `__init__.py` so packages aren’t recognized.
* Hitting the wrong path because of a prefix or `chat:turn` vs `chat/turn`.

# Success signal

Once the server starts cleanly and `/docs` shows your route, your earlier 404s will disappear. If anything still blocks you, paste:

* the route dump from `main.py`
* the exact URL you’re posting to
* the first ~20 lines of `main.py` and `llm.py` after edits

I’ll pinpoint the next line to flip.
