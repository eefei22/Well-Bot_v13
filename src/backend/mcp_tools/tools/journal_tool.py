"""
Journal tools following Global LLD.
Handles journal session start, stop, and save operations.
"""

from envelopes import Card, ok_card, overlay_control, Diagnostics
from typing import Dict, Any


async def start(ctx, req) -> Card:
    """
    Start a journal overlay session.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope
        
    Returns:
        Overlay control card to start journaling
    """
    return overlay_control(
        title="Journal Session Started",
        body="I'm listening to your thoughts. Speak naturally, and I'll help you capture your reflections.",
        meta={"kind": "journal", "action": "start_overlay"},
        diagnostics=Diagnostics(
            tool="journal.start",
            duration_ms=ctx.timing.timing()
        )
    )


async def stop(ctx, req) -> Card:
    """
    Stop the journal overlay session.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope
        
    Returns:
        Card confirming journal session end
    """
    return ok_card(
        title="Journal Session Ended",
        body="Journal session completed. Your thoughts have been captured.",
        meta={"kind": "journal"},
        diagnostics=Diagnostics(
            tool="journal.stop",
            duration_ms=ctx.timing.timing()
        )
    )


async def save(ctx, req) -> Card:
    """
    Save journal entry (draft or final).
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with title, body, mood, topics, is_draft
        
    Returns:
        Card confirming save operation
    """
    title = req.args.get("title", "Untitled Entry")
    body = req.args.get("body", "")
    mood = req.args.get("mood", 3)  # 1-5 scale
    topics = req.args.get("topics", [])
    is_draft = req.args.get("is_draft", False)
    
    # Placeholder save logic
    # In real implementation, would save to wb_journal table
    
    status = "draft" if is_draft else "final"
    
    return ok_card(
        title="Journal Entry Saved",
        body=f"Your journal entry '{title}' has been saved as {status}.",
        meta={"kind": "journal", "status": status},
        diagnostics=Diagnostics(
            tool="journal.save",
            duration_ms=ctx.timing.timing()
        )
    )
