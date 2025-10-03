"""
fastMCP server application following ADD_MCP.md pattern.
Bootstrap server with middleware and tool registration.
"""

import os
import structlog
from fastmcp import MCPApp
from middleware import auth_mw, envelope_mw, error_mw, timing_mw

# Import tool modules
from tools import test_tool, session_tool, safety_tool, memory_tool
from tools import journal_tool, todo_tool, gratitude_tool, quote_tool, meditation_tool

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create fastMCP app
app = MCPApp()

# Global middlewares (order matters)
app.use(timing_mw)     # Start/stop timers, add duration_ms
app.use(auth_mw)       # Validate Supabase JWT or static key; attach user_id
app.use(envelope_mw)   # Validate MCPRequest; ensure response is Card shape
app.use(error_mw)      # Map exceptions -> error_card consistently

# Tool registration (names must match HLD/LLD)
# Test tool
app.tool("test.hello")(test_tool.hello)

# Session tools
app.tool("session.wake")(session_tool.wake)
app.tool("session.end")(session_tool.end)

# Safety tool
app.tool("safety.check")(safety_tool.check)

# Memory tool
app.tool("memory.search")(memory_tool.search)

# Journal tools
app.tool("journal.start")(journal_tool.start)
app.tool("journal.stop")(journal_tool.stop)
app.tool("journal.save")(journal_tool.save)

# Gratitude tool
app.tool("gratitude.add")(gratitude_tool.add)

# Todo tools
app.tool("todo.add")(todo_tool.add)
app.tool("todo.list")(todo_tool.list)
app.tool("todo.complete")(todo_tool.complete)
app.tool("todo.delete")(todo_tool.delete)

# Quote tool
app.tool("quote.get")(quote_tool.get)

# Meditation tools
app.tool("meditation.play")(meditation_tool.play)
app.tool("meditation.cancel")(meditation_tool.cancel)
app.tool("meditation.restart")(meditation_tool.restart)
app.tool("meditation.log")(meditation_tool.log)

# Activity event tool
app.tool("activityevent.log")(activity_tool.log)

logger.info("fastMCP server initialized", tools_registered=len(app.tools))

if __name__ == "__main__":
    host = os.getenv("FASTMCP_HOST", "0.0.0.0")
    port = int(os.getenv("FASTMCP_PORT", "8000"))
    
    logger.info("Starting fastMCP server", host=host, port=port)
    app.run(host=host, port=port)
