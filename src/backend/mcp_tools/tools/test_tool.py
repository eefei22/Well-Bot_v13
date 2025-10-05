"""
Test tool implementation following ADD_MCP.md pattern.
Simple "hello world" tool to validate the infrastructure.
"""

from ..envelopes import Card, ok_card, Diagnostics
from typing import Dict, Any


async def hello(ctx, req) -> Card:
    """
    Test tool that returns a greeting.
    
    Args:
        ctx: FastMCP context with timing and other middleware data
        req: MCPRequest envelope
        
    Returns:
        Card with greeting message
    """
    # Extract name from args, default to "friend"
    name = req.args.get("name", "friend")
    
    # Create greeting message
    greeting = f"Hello, {name}!"
    
    # Return success card
    return ok_card(
        title="Hello",
        body=greeting,
        meta={"kind": "info"},
        diagnostics=Diagnostics(
            tool="test.hello",
            duration_ms=ctx.timing.timing()
        )
    )
