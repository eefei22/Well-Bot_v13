"""
Session management tools following Global LLD.
Handles session wake and end operations.
"""

from envelopes import Card, ok_card, Diagnostics
from typing import Dict, Any


async def wake(ctx, req) -> Card:
    """
    Start a new session.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope
        
    Returns:
        Card confirming session start
    """
    return ok_card(
        title="Session Started",
        body="Welcome! I'm here to help with your wellness journey. What would you like to do today?",
        meta={"kind": "info"},
        diagnostics=Diagnostics(
            tool="session.wake",
            duration_ms=ctx.timing.timing()
        )
    )


async def end(ctx, req) -> Card:
    """
    End the current session.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with reason
        
    Returns:
        Card confirming session end
    """
    reason = req.args.get("reason", "manual")
    
    if reason == "manual":
        message = "Session ended. Take care and see you next time!"
    elif reason == "inactivity":
        message = "It seems like you're not around, I'll just go take a break now."
    else:
        message = "Session ended. Goodbye!"
    
    return ok_card(
        title="Session Ended",
        body=message,
        meta={"kind": "info", "reason": reason},
        diagnostics=Diagnostics(
            tool="session.end",
            duration_ms=ctx.timing.timing()
        )
    )
