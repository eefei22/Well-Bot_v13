<!-- 14c3e0fe-cdbc-4d87-ae1a-8b2ebde92ae5 c936363a-b89c-474b-9973-1aad2eb6326b -->
# Fix LLM Environment Variable Loading and Error Handling

## Root Cause Analysis

### Issue 1: Environment Variables Not Loading at Import Time

**Problem:** The DeepSeek client is being initialized when `llm.py` imports `chat_completion`, which happens BEFORE the FastAPI app's `load_dotenv()` is called in `main.py`.

**Evidence:**

- `main.py` line 24 calls `load_dotenv()`
- `main.py` line 20 imports `llm_router` from `llm.py`
- `llm.py` line 19 imports `chat_completion` from `deepseek.py`
- `deepseek.py` line 326-331 creates global `_client` on first call to `get_deepseek_client()`
- When `get_deepseek_client()` is called, `os.getenv("DEEPSEEK_API_KEY")` returns `None` because `.env` hasn't been loaded yet

**Import Order:**

```
uvicorn starts → import main.py → import llm_router → import chat_completion 
→ call get_deepseek_client() → DeepSeekClient.__init__() → os.getenv("DEEPSEEK_API_KEY") = None
→ raise ValueError → (catches, returns error card)
```

### Issue 2: Error Swallowing

The error is caught in the try-except block at line 362-379 of `llm.py`, but the actual exception message isn't visible in the API response (only shows generic "I'm having trouble responding right now").

## Fix Strategy

### Fix 1: Move dotenv Loading Earlier

**File: `src/backend/services/deepseek.py`**

Add `load_dotenv()` at the TOP of the module, before any class definitions:

```python
"""
DeepSeek LLM service adapter using OpenAI SDK with base_url override.
Provides streaming and non-streaming chat completion with intent classification.
"""

import os
import hashlib
import asyncio
import structlog
from typing import Dict, Any, List, Optional, AsyncIterator, Union
from dotenv import load_dotenv  # ADD THIS
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
import time
from datetime import datetime, timezone

# Load environment variables FIRST
load_dotenv()  # ADD THIS

logger = structlog.get_logger()
```

This ensures `.env` is loaded before the DeepSeekClient class is ever instantiated.

### Fix 2: Add Detailed Error Logging

**File: `src/backend/api/routes/llm.py`**

Update the exception handler at line 362-379 to log the ACTUAL error:

```python
except Exception as e:
    logger.error(
        "DeepSeek completion failed",
        turn_id=turn_id,
        error=str(e),
        error_type=type(e).__name__  # ADD THIS
    )
    
    # Fail-open to error card
    return error_card(
        title="Chat Error",
        body="I'm having trouble responding right now. Please try again.",
        error_code="LLM_COMPLETION_FAILED",
        tool="llm.chat_turn",
        diagnostics=Diagnostics(
            tool="llm.chat_turn",
            duration_ms=int((time.time() - start_time) * 1000)
        )
    )
```

### Fix 3: Add Client Initialization Verification

**File: `src/backend/services/deepseek.py`**

Improve error message in `__init__` to help diagnose issues:

```python
def __init__(self):
    self.api_key = os.getenv("DEEPSEEK_API_KEY")
    self.base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    
    if not self.api_key:
        # IMPROVE ERROR MESSAGE
        logger.error(
            "DEEPSEEK_API_KEY not found in environment",
            env_file_exists=os.path.exists(".env"),
            cwd=os.getcwd()
        )
        raise ValueError(
            "DEEPSEEK_API_KEY environment variable is required. "
            "Ensure .env file exists and contains DEEPSEEK_API_KEY=your-key"
        )
```

### Fix 4: Add Health Check for LLM

**File: `src/backend/api/routes/llm.py`**

Add a simple health check endpoint to verify LLM connectivity:

```python
@router.get("/health")
async def llm_health() -> Dict[str, Any]:
    """
    Health check for LLM service.
    Returns initialization status and basic config.
    """
    try:
        from src.backend.services.deepseek import get_deepseek_client
        client = get_deepseek_client()
        
        return {
            "status": "healthy",
            "model": client.model,
            "base_url": client.base_url,
            "api_key_set": bool(client.api_key),
            "streaming_enabled": client.streaming_enabled
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "error_type": type(e).__name__
        }
```

## Investigation Steps

### Step 1: Verify Environment Loading

Test that dotenv loads correctly:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API_KEY:', os.getenv('DEEPSEEK_API_KEY')[:20])"
```

### Step 2: Test DeepSeek Client Directly

After fixes, test client initialization:

```bash
python -c "from src.backend.services.deepseek import get_deepseek_client; client = get_deepseek_client(); print('Client OK:', client.model)"
```

### Step 3: Test LLM Health Endpoint

After server restart:

```bash
curl http://localhost:8000/llm/health
```

### Step 4: Test Chat Turn with Detailed Logs

Monitor backend logs while sending a test message to see actual errors.

## Expected Results

After fixes:

- DeepSeek client initializes successfully on server startup
- Environment variables load before any client instantiation
- Error logs show actual exception details, not generic messages
- Health endpoint shows LLM status
- Chat turn endpoint returns actual LLM responses or specific error details

## Files to Modify

1. `src/backend/services/deepseek.py` - Add early `load_dotenv()` and better error messages
2. `src/backend/api/routes/llm.py` - Add health endpoint and detailed error logging
3. No frontend changes needed (this is backend-only)

## Testing Checklist

- [ ] Server starts without errors
- [ ] `/llm/health` endpoint returns `status: healthy`
- [ ] Chat turn with "Hello" returns actual LLM response
- [ ] Error logs show detailed exception info if failures occur
- [ ] Conversation and messages are stored in database

### To-dos

- [ ] Fix all relative import paths in ChatPage.tsx (add extra ../)
- [ ] Activate venv and install openai package
- [ ] Verify all __init__.py files exist in backend folders
- [ ] Restart both servers and test basic functionality
- [ ] Update tsconfig.json with baseUrl and paths for @ alias
- [ ] Update vite.config.ts with path import and resolve.alias
- [ ] Refactor all imports to use @/ alias pattern
- [ ] Test full E2E flow after all fixes