# MCP Tools Infrastructure

FastMCP-based tool server for Well-Bot following the ADD_MCP.md pattern.

## Structure

```
mcp_tools/
├── envelopes.py          # Request/response models and helpers
├── middleware.py         # Auth, validation, error handling, timing
├── app.py               # FastMCP server bootstrap
├── tools/               # Individual tool implementations
│   ├── test_tool.py     # test.hello - infrastructure validation
│   ├── session_tool.py  # session.wake, session.end
│   ├── safety_tool.py   # safety.check
│   ├── memory_tool.py   # memory.search
│   ├── journal_tool.py  # journal.start, journal.stop, journal.save
│   ├── todo_tool.py     # todo.add, todo.list, todo.complete, todo.delete
│   ├── gratitude_tool.py # gratitude.add
│   ├── quote_tool.py    # quote.get
│   ├── meditation_tool.py # meditation.play, meditation.cancel, etc.
│   └── activity_tool.py # activityevent.log
└── test_infrastructure.py # Simple validation script
```

## Environment Variables

```bash
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
FASTMCP_AUTH_MODE=supabase|static
FASTMCP_AUTH_KEY=dev-secret
```

## Usage

### Run Infrastructure Test
```bash
cd src/backend/mcp_tools
python test_infrastructure.py
```

### Start FastMCP Server
```bash
cd src/backend/mcp_tools
python app.py
```

## Tool Pattern

Each tool follows this pattern:

```python
async def tool_name(ctx, req) -> Card:
    """
    Tool description.
    
    Args:
        ctx: FastMCP context with timing and middleware data
        req: MCPRequest envelope
        
    Returns:
        Card response
    """
    # Extract args
    param = req.args.get("param", "default")
    
    # Tool logic here
    
    # Return response
    return ok_card(
        title="Success Title",
        body="Response body",
        meta={"kind": "tool_type"},
        diagnostics=Diagnostics(
            tool="tool.name",
            duration_ms=ctx.timing.timing()
        )
    )
```

## Global Envelope Structure

### Request (MCPRequest)
```json
{
  "trace_id": "string",
  "user_id": "string", 
  "conversation_id": "string?",
  "session_id": "string?",
  "args": {},
  "ts_utc": "ISO-8601"
}
```

### Response (Card)
```json
{
  "status": "ok|error",
  "type": "card|overlay_control|error_card",
  "title": "string",
  "body": "string", 
  "meta": {"kind": "tool_type"},
  "persisted_ids": {"primary_id": "uuid", "extra": []},
  "diagnostics": {"tool": "string", "duration_ms": 0},
  "error_code": "string?"
}
```

## Middleware Stack

1. **timing_mw** - Track request duration
2. **auth_mw** - Validate authentication (JWT or static key)
3. **envelope_mw** - Validate request format, ensure Card response
4. **error_mw** - Map exceptions to error cards

## Status

✅ **Core Infrastructure** - Envelopes, middleware, app bootstrap  
✅ **Test Tool** - test.hello validates the pattern  
✅ **Session Tools** - session.wake, session.end  
✅ **Safety Tool** - safety.check with basic phrase detection  
✅ **Memory Tool** - memory.search with mock RAG  
✅ **Activity Tools** - All tools implemented with placeholder logic  

**Next Steps:**
- Integrate with actual Supabase database
- Add real embeddings/RAG implementation
- Add comprehensive error handling
- Add logging to wb_tool_invocation_log table
