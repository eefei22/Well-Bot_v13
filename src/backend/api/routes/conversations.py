"""
Conversation management API endpoints for Well-Bot.
Provides CRUD operations for conversations and messages.
"""

import asyncio
import time
import structlog
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

# Add the backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.backend.services.database import get_db_client

logger = structlog.get_logger()
router = APIRouter()


class ConversationResponse(BaseModel):
    """Response schema for conversation data."""
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class MessageResponse(BaseModel):
    """Response schema for message data."""
    id: str
    conversation_id: str
    role: str
    content: str
    created_at: str
    metadata: Optional[Dict[str, Any]] = None


class CreateConversationRequest(BaseModel):
    """Request schema for creating a conversation."""
    user_id: str
    title: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Request schema for sending a message."""
    conversation_id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


@router.get("/conversations/{user_id}")
async def get_conversations(user_id: str) -> List[ConversationResponse]:
    """
    Get all conversations for a user, ordered by most recent.
    
    Args:
        user_id: User identifier
        
    Returns:
        List of conversations with metadata
    """
    start_time = time.time()
    
    try:
        db = get_db_client()
        
        # Get conversations with message counts
        result = db.table("wb_conversation").select(
            "id, user_id, started_at, ended_at, wb_message(count)"
        ).eq("user_id", user_id).order("started_at", desc=True).execute()
        
        conversations = []
        for conv in result.data:
            conversations.append(ConversationResponse(
                id=conv["id"],
                user_id=conv["user_id"],
                title=f"Conversation {conv['started_at'][:10]}",  # Use date as title
                created_at=conv["started_at"],
                updated_at=conv["ended_at"] or conv["started_at"],
                message_count=len(conv.get("wb_message", []))
            ))
        
        logger.info(
            "Retrieved conversations",
            user_id=user_id,
            count=len(conversations),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return conversations
        
    except Exception as e:
        logger.error(
            "Failed to retrieve conversations",
            user_id=user_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversations: {str(e)}")


@router.post("/conversations")
async def create_conversation(request: CreateConversationRequest) -> ConversationResponse:
    """
    Create a new conversation.
    
    Args:
        request: Conversation creation data
        
    Returns:
        Created conversation data
    """
    start_time = time.time()
    
    try:
        db = get_db_client()
        
        # Create conversation
        conversation_data = {
            "user_id": request.user_id,
            "started_at": "now()",
            "ended_at": None
        }
        
        result = db.table("wb_conversation").insert(conversation_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create conversation")
        
        conv = result.data[0]
        
        logger.info(
            "Created conversation",
            conversation_id=conv["id"],
            user_id=request.user_id,
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return ConversationResponse(
            id=conv["id"],
            user_id=conv["user_id"],
            title=f"Conversation {conv['started_at'][:10]}",
            created_at=conv["started_at"],
            updated_at=conv["ended_at"] or conv["started_at"],
            message_count=0
        )
        
    except Exception as e:
        logger.error(
            "Failed to create conversation",
            user_id=request.user_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str) -> List[MessageResponse]:
    """
    Get all messages for a conversation.
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        List of messages in chronological order
    """
    start_time = time.time()
    
    try:
        db = get_db_client()
        
        result = db.table("wb_message").select("*").eq(
            "conversation_id", conversation_id
        ).order("created_at", desc=False).execute()
        
        messages = []
        for msg in result.data:
            messages.append(MessageResponse(
                id=msg["id"],
                conversation_id=msg["conversation_id"],
                role=msg["role"],
                content=msg["text"],  # Use 'text' field from database
                created_at=msg["created_at"],
                metadata=None  # No metadata field in schema
            ))
        
        logger.info(
            "Retrieved messages",
            conversation_id=conversation_id,
            count=len(messages),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return messages
        
    except Exception as e:
        logger.error(
            "Failed to retrieve messages",
            conversation_id=conversation_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=500, detail=f"Failed to retrieve messages: {str(e)}")


@router.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: str, request: SendMessageRequest) -> MessageResponse:
    """
    Send a message to a conversation.
    
    Args:
        conversation_id: Conversation identifier
        request: Message data
        
    Returns:
        Created message data
    """
    start_time = time.time()
    
    try:
        db = get_db_client()
        
        # Create message
        message_data = {
            "conversation_id": conversation_id,
            "role": request.role,
            "text": request.content,  # Use 'text' field for database
            "created_at": "now()"
        }
        
        result = db.table("wb_message").insert(message_data).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create message")
        
        msg = result.data[0]
        
        # Update conversation timestamp
        db.table("wb_conversation").update({
            "ended_at": "now()"
        }).eq("id", conversation_id).execute()
        
        logger.info(
            "Created message",
            message_id=msg["id"],
            conversation_id=conversation_id,
            role=request.role,
            content_length=len(request.content),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return MessageResponse(
            id=msg["id"],
            conversation_id=msg["conversation_id"],
            role=msg["role"],
            content=msg["text"],  # Use 'text' field from database
            created_at=msg["created_at"],
            metadata=None
        )
        
    except Exception as e:
        logger.error(
            "Failed to create message",
            conversation_id=conversation_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=500, detail=f"Failed to create message: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> Dict[str, str]:
    """
    Delete a conversation and all its messages.
    
    Args:
        conversation_id: Conversation identifier
        
    Returns:
        Success confirmation
    """
    start_time = time.time()
    
    try:
        db = get_db_client()
        
        # Delete messages first (foreign key constraint)
        db.table("wb_message").delete().eq("conversation_id", conversation_id).execute()
        
        # Delete conversation
        db.table("wb_conversation").delete().eq("id", conversation_id).execute()
        
        logger.info(
            "Deleted conversation",
            conversation_id=conversation_id,
            duration_ms=int((time.time() - start_time) * 1000)
        )
        
        return {"message": "Conversation deleted successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to delete conversation",
            conversation_id=conversation_id,
            error=str(e),
            duration_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")
