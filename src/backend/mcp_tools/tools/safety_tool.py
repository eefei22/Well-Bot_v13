"""
Safety tool following Global LLD.
Checks user input for concerning content and provides support resources.
"""

from envelopes import Card, ok_card, error_card, Diagnostics
from typing import Dict, Any


async def check(ctx, req) -> Card:
    """
    Check user input for safety concerns.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with text, lang, context, session_ts
        
    Returns:
        Card with safety check result
    """
    text = req.args.get("text", "")
    lang = req.args.get("lang", "en")
    context = req.args.get("context", "chat")
    session_ts = req.args.get("session_ts")
    
    # Basic safety check (placeholder - would integrate with actual safety service)
    # For now, just check for obvious concerning phrases
    concerning_phrases = [
        "hurt myself", "kill myself", "end it all", "not worth living",
        "suicide", "self harm", "cut myself", "overdose"
    ]
    
    text_lower = text.lower()
    found_concerns = [phrase for phrase in concerning_phrases if phrase in text_lower]
    
    if found_concerns:
        # Show support resources
        return ok_card(
            title="Support Resources",
            body="If you're having thoughts of self-harm, please reach out for help. You can contact the National Suicide Prevention Lifeline at 988 or text HOME to 741741 for crisis support. You're not alone, and there are people who care about you.",
            meta={
                "kind": "info",
                "action": "show_support_card",
                "concerns_found": found_concerns
            },
            diagnostics=Diagnostics(
                tool="safety.check",
                duration_ms=ctx.timing.timing()
            )
        )
    else:
        # No concerns found
        return ok_card(
            title="Safety Check Complete",
            body="No safety concerns detected.",
            meta={
                "kind": "info", 
                "action": "none"
            },
            diagnostics=Diagnostics(
                tool="safety.check",
                duration_ms=ctx.timing.timing()
            )
        )
