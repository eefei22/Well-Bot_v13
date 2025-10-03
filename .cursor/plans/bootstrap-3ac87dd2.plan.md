<!-- 3ac87dd2-1686-46ca-b7d2-b39dc11f23b6 6f8a6ec8-c87b-4ab4-89f9-9b3bea303f86 -->
# FastAPI Backend Bootstrap (Liveness + Readiness)

## Assumptions (can adjust)

- Run FastAPI and fastMCP as separate processes: API on 8080, fastMCP on 8000.
- Dev CORS origin: `http://localhost:5173` (Vite).
- Env keys for DB match current code: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`.

## Files to Add

- `src/backend/api/main.py`
  - Create FastAPI app, enable CORS, include health router, structlog logging.
  - Read `API_HOST` (default `0.0.0.0`) and `API_PORT` (default `8080`).
- `src/backend/api/routes/health.py`
  - `GET /healthz` (liveness): returns `{status:"ok", service:"api", version, time}`.
  - `GET /readyz` (readiness): calls `services.database.health_check()`; returns DB status and details.
- `src/backend/api/__init__.py` and `src/backend/api/routes/__init__.py` (module init).

## Key Snippets (concise)

```python
# src/backend/api/routes/health.py
from fastapi import APIRouter
from datetime import datetime, timezone
from src.backend.services.database import health_check as db_health

router = APIRouter()

@router.get("/healthz")
def healthz():
    return {"status":"ok","service":"api","time": datetime.now(timezone.utc).isoformat()}

@router.get("/readyz")
async def readyz():
    db = await db_health()
    return {"status": ("ok" if db.get("status")=="healthy" else "error"), "db": db}
```



```python
# src/backend/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.backend.api.routes.health import router as health_router

app = FastAPI(title="Well-Bot API")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(health_router)
```

## Env

- `.env` (dev):
  - `SUPABASE_URL=...`
  - `SUPABASE_SERVICE_ROLE_KEY=...`
  - `API_HOST=0.0.0.0`
  - `API_PORT=8080`

## Run

- Windows PowerShell:
  - `venv\Scripts\python -m uvicorn src.backend.api.main:app --host 0.0.0.0 --port 8080 --reload`
- Verify:
  - `GET http://localhost:8080/healthz` → `{"status":"ok"}`
  - `GET http://localhost:8080/readyz` → includes DB status from Supabase

## Optional (nice-to-have)

- `GET /mcpz` simple check to confirm fastMCP port responds (HTTP ping or omit if separate transport).
- Add `tests/integration/test_health_endpoints.py` using `httpx` to assert 200 and payload keys.

### To-dos

- [ ] Create `src/backend/api/main.py` FastAPI app with CORS and router
- [ ] Add `src/backend/api/routes/health.py` with /healthz and /readyz endpoints
- [ ] Ensure env loading and structlog consistent with services layer
- [ ] Run uvicorn; verify /healthz and /readyz return expected payloads
- [ ] Create integration tests for health endpoints with httpx