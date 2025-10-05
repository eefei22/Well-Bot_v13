"""
LLM chat turn handler with safety-first pipeline and standard envelope contract.
Provides /llm/chat:turn endpoint with intent detection and routing.
"""

import asyncio
import time
import structlog
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.backend.services.deepseek import chat_completion
from src.backend.core.intent_detector import detect_intent
from src.backend.mcp_tools.tools.safety_tool import check as safety_check
from src.backend.mcp_tools.envelopes import Card, ok_card, error_card, Diagnostics

logger = structlog.get_logger()
router = APIRouter()


class ChatTurnRequest(BaseModel):
    """Request schema for chat turn endpoint."""
    text: str
    user_id: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None


def generate_stub_card(intent: str, args: Dict[str, Any]) -> Card:
    """
    Generate stub cards for tool intents with consistent meta.kind.
    
    Args:
        intent: Detected intent
        args: Extracted arguments
        
    Returns:
        Card with appropriate title, body, and meta
    """
    stub_cards = {
        "journal.start": {
            "title": "Journal Session",
            "body": "Opening your journal overlay... (stub)",
            "meta": {"kind": "journal"}
        },
        "gratitude.add": {
            "title": "Gratitude Added", 
            "body": "I've noted your gratitude entry. (stub)",
            "meta": {"kind": "gratitude"}
        },
        "todo.add": {
            "title": "To-Do Added",
            "body": "Added to your to-do list. (stub)",
            "meta": {"kind": "todo"}
        },
        "todo.list": {
            "title": "Your To-Dos",
            "body": "Here are your open tasks... (stub)",
            "meta": {"kind": "todo"}
        },
        "todo.complete": {
            "title": "To-Do Completed",
            "body": "Marked as completed. (stub)",
            "meta": {"kind": "todo"}
        },
        "todo.delete": {
            "title": "To-Do Deleted",
            "body": "Removed from your list. (stub)",
            "meta": {"kind": "todo"}
        },
        "quote.get": {
            "title": "Spiritual Quote",
            "body": "Here's a quote for reflection... (stub)",
            "meta": {"kind": "quote"}
        },
        "meditation.play": {
            "title": "Meditation Starting",
            "body": "Preparing your meditation... (stub)",
            "meta": {"kind": "meditation"}
        },
        "session.end": {
            "title": "Session Ending",
            "body": "Take care, talk soon! (stub)",
            "meta": {"kind": "info"}
        }
    }
    
    card_data = stub_cards.get(intent, {
        "title": "Action Completed",
        "body": "Your request has been processed. (stub)",
        "meta": {"kind": "info"}
    })
    
    return ok_card(
        title=card_data["title"],
        body=card_data["body"],
        meta=card_data["meta"],
        diagnostics=Diagnostics(
            tool="llm.chat_turn",
            duration_ms=0  # Will be updated by caller
        )
    )


async def run_safety_check(text: str, user_id: str, session_id: Optional[str] = None) -> Optional[Card]:
    """
    Run safety check with 50ms timeout and fail-open behavior.
    
    Args:
        text: User input text
        user_id: User ID
        session_id: Session ID
        
    Returns:
        Support card if triggered, None if safe
    """
    try:
        # Create mock request envelope for safety tool
        from mcp_tools.envelopes import MCPRequest
        from datetime import datetime, timezone
        
        req = MCPRequest(
            trace_id="safety_check",
            user_id=user_id,
            session_id=session_id or "unknown",
            args={
                "text": text,
                "lang": "en",
                "context": "chat",
                "session_ts": datetime.now(timezone.utc).isoformat()
            },
            ts_utc=datetime.now(timezone.utc).isoformat()
        )
        
        # Run safety check with timeout
        safety_result = await asyncio.wait_for(
            safety_check(None, req),  # None for context (safety tool doesn't use it)
            timeout=0.05  # 50ms timeout
        )
        
        # Check if safety was triggered
        if safety_result.meta.get("action") == "show_support_card":
            logger.info(
                "Safety check triggered",
                action=safety_result.meta.get("action"),
                masked_text=text[:20] + "..." if len(text) > 20 else text
            )
            return safety_result
        
        return None
        
    except asyncio.TimeoutError:
        logger.warning("Safety check timeout, continuing turn")
        return None
    except Exception as e:
        logger.error("Safety check failed, continuing turn", error=str(e))
        return None


@router.post("/chat/turn")
async def chat_turn(request: ChatTurnRequest) -> Card:
    """
    Process a chat turn with safety-first pipeline and intent routing.
    
    Pipeline:
    1. Safety check (50ms timeout, fail-open)
    2. Intent detection (regex + LLM)
    3. Route to small-talk (DeepSeek) or stub card (tool intent)
    
    Returns:
        Standard card envelope with status, diagnostics
    """
    start_time = time.time()
    turn_id = request.trace_id or f"turn_{int(start_time)}"
    
    logger.info(
        "Processing chat turn",
        turn_id=turn_id,
        user_id=request.user_id,
        text_length=len(request.text),
        masked_text=request.text[:20] + "..." if len(request.text) > 20 else request.text
    )
    
    try:
        # Step 1: Safety check (first, fast, fail-open)
        safety_card = await run_safety_check(
            request.text, 
            request.user_id, 
            request.session_id
        )
        
        if safety_card:
            # Safety triggered - short-circuit and return support card
            safety_card.diagnostics.duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                "Turn completed - safety triggered",
                turn_id=turn_id,
                duration_ms=safety_card.diagnostics.duration_ms
            )
            return safety_card
        
        # Step 2: Intent detection
        intent_result = await detect_intent(request.text)
        intent = intent_result["intent"]
        confidence = intent_result["confidence"]
        args = intent_result["args"]
        
        logger.info(
            "Intent detected",
            turn_id=turn_id,
            intent=intent,
            confidence=confidence,
            args=args
        )
        
        # Step 3: Route based on intent
        if intent == "small_talk":
            # Generate DeepSeek response
            messages = [
                {"role": "system", "content": "You are a warm, supportive wellness assistant. Keep responses concise and helpful."},
                {"role": "user", "content": request.text}
            ]
            
            try:
                response_text = await chat_completion(messages, stream=False)
                
                card = ok_card(
                    title="Chat Response",
                    body=response_text,
                    meta={"kind": "info"},
                    diagnostics=Diagnostics(
                        tool="llm.chat_turn",
                        duration_ms=int((time.time() - start_time) * 1000)
                    )
                )
                
                logger.info(
                    "Turn completed - small talk",
                    turn_id=turn_id,
                    intent=intent,
                    response_length=len(response_text),
                    duration_ms=card.diagnostics.duration_ms
                )
                
                return card
                
            except Exception as e:
                logger.error(
                    "DeepSeek completion failed",
                    turn_id=turn_id,
                    error=str(e)
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
        
        else:
            # Tool intent - return stub card
            card = generate_stub_card(intent, args)
            card.diagnostics.duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Turn completed - tool intent",
                turn_id=turn_id,
                intent=intent,
                duration_ms=card.diagnostics.duration_ms
            )
            
            return card
    
    except Exception as e:
        logger.error(
            "Chat turn failed",
            turn_id=turn_id,
            error=str(e),
            error_type=type(e).__name__
        )
        
        return error_card(
            title="Processing Error",
            body="Something went wrong processing your request. Please try again.",
            error_code="TURN_PROCESSING_FAILED",
            tool="llm.chat_turn",
            diagnostics=Diagnostics(
                tool="llm.chat_turn",
                duration_ms=int((time.time() - start_time) * 1000)
            )
        )
