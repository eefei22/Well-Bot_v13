"""
Gratitude tool following Global LLD.
Handles adding gratitude entries.
"""

from ..envelopes import Card, ok_card, Diagnostics
from typing import Dict, Any


async def add(ctx, req) -> Card:
    """
    Add a gratitude entry.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with text
        
    Returns:
        Card confirming gratitude entry saved
    """
    text = req.args.get("text", "")
    
    if not text.strip():
        return Card(
            status="error",
            type="error_card",
            title="Validation Error",
            body="Gratitude text cannot be empty",
            meta={"tool": "gratitude.add", "error_code": "VALIDATION_ERROR"},
            diagnostics=Diagnostics(tool="gratitude.add", duration_ms=ctx.timing.timing()),
            error_code="VALIDATION_ERROR"
        )
    
    # Placeholder add logic
    # In real implementation, would:
    # 1. Truncate to 100 words with "..."
    # 2. Convert to Sentence case
    # 3. Save to wb_gratitude_item table
    # 4. Embed for RAG
    
    # Truncate if needed
    words = text.split()
    if len(words) > 100:
        truncated_text = " ".join(words[:100]) + "..."
    else:
        truncated_text = text
    
    return ok_card(
        title="Gratitude Saved",
        body=f"Saved: {truncated_text}",
        meta={"kind": "gratitude"},
        diagnostics=Diagnostics(
            tool="gratitude.add",
            duration_ms=ctx.timing.timing()
        )
    )
