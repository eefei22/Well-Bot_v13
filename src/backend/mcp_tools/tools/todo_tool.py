"""
Todo tools following Global LLD.
Handles todo add, list, complete, and delete operations.
"""

from ..envelopes import Card, ok_card, Diagnostics
from typing import Dict, Any


async def add(ctx, req) -> Card:
    """
    Add todo items.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with titles list
        
    Returns:
        Card showing updated todo list
    """
    titles = req.args.get("titles", [])
    return_list_after = req.args.get("return_list_after", True)
    
    # Placeholder add logic
    # In real implementation, would:
    # 1. Normalize titles (Title Case, truncate >20 words)
    # 2. Cap at 10 items
    # 3. Save to wb_todo_item table
    # 4. Embed titles for RAG
    
    added_count = min(len(titles), 10)
    
    if return_list_after:
        # Mock current open todos
        mock_todos = [
            "Complete project proposal",
            "Call dentist for appointment", 
            "Buy groceries for weekend"
        ]
        
        body = "To-Do List (Updated):\n" + "\n".join([f"• {todo}" for todo in mock_todos])
    else:
        body = f"Added {added_count} items to your to-do list."
    
    return ok_card(
        title="To-Do Items Added",
        body=body,
        meta={"kind": "todo", "items_added": added_count},
        diagnostics=Diagnostics(
            tool="todo.add",
            duration_ms=ctx.timing.timing()
        )
    )


async def list(ctx, req) -> Card:
    """
    List open todo items.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope
        
    Returns:
        Card showing open todos
    """
    # Placeholder list logic
    mock_todos = [
        {"id": "1", "title": "Complete project proposal", "created_at": "2024-01-15T10:00:00Z"},
        {"id": "2", "title": "Call dentist for appointment", "created_at": "2024-01-14T15:30:00Z"},
        {"id": "3", "title": "Buy groceries for weekend", "created_at": "2024-01-14T09:15:00Z"}
    ]
    
    if mock_todos:
        body = "Your open to-do items:\n" + "\n".join([f"• {todo['title']}" for todo in mock_todos])
    else:
        body = "Your to-do list is empty."
    
    return ok_card(
        title="To-Do List",
        body=body,
        meta={"kind": "todo", "count": len(mock_todos)},
        diagnostics=Diagnostics(
            tool="todo.list",
            duration_ms=ctx.timing.timing()
        )
    )


async def complete(ctx, req) -> Card:
    """
    Complete a todo item.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with item_id or title
        
    Returns:
        Card confirming completion
    """
    item_id = req.args.get("item_id")
    title = req.args.get("title", "")
    
    # Placeholder complete logic
    return ok_card(
        title="To-Do Completed",
        body=f"Marked '{title}' as completed. Great job!",
        meta={"kind": "todo", "action": "complete"},
        diagnostics=Diagnostics(
            tool="todo.complete",
            duration_ms=ctx.timing.timing()
        )
    )


async def delete(ctx, req) -> Card:
    """
    Delete a todo item.
    
    Args:
        ctx: FastMCP context
        req: MCPRequest envelope with item_id or title
        
    Returns:
        Card confirming deletion
    """
    item_id = req.args.get("item_id")
    title = req.args.get("title", "")
    
    # Placeholder delete logic
    return ok_card(
        title="To-Do Deleted",
        body=f"Deleted '{title}' from your to-do list.",
        meta={"kind": "todo", "action": "delete"},
        diagnostics=Diagnostics(
            tool="todo.delete",
            duration_ms=ctx.timing.timing()
        )
    )
