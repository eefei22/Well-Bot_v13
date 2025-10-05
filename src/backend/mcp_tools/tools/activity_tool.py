"""
Activity event logging tool following Global LLD.
Logs various user activities for analytics.
"""

from ..envelopes import Card, ok_card, Diagnostics
from typing import Dict, Any


async def log(ctx, req) -> Card:
    """
    Log an activity event.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with type, ref_id, action
        
    Returns:
        Card confirming log entry
    """
    event_type = req.args.get("type", "")
    ref_id = req.args.get("ref_id")
    action = req.args.get("action", "")
    
    # Placeholder logging logic
    # In real implementation, would save to wb_activity_event table
    
    return ok_card(
        title="Activity Logged",
        body=f"Logged {event_type} activity: {action}",
        meta={"kind": "info", "event_type": event_type},
        diagnostics=Diagnostics(
            tool="activityevent.log",
            duration_ms=ctx.timing.timing()
        )
    )
