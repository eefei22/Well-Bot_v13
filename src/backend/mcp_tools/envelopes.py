"""
Global envelope models for MCP tools following ADD_MCP.md pattern.
Compatible with Global LLD requirements.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from uuid import UUID


class MCPRequest(BaseModel):
    """Request envelope for all MCP tools."""
    trace_id: str
    user_id: str
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    args: Dict[str, Any] = Field(default_factory=dict)
    ts_utc: str


class Diagnostics(BaseModel):
    """Diagnostic information for responses."""
    tool: str
    duration_ms: int
    memory_used: Optional[bool] = None
    memory_latency_ms: Optional[int] = None


class PersistedIds(BaseModel):
    """IDs of persisted entities."""
    primary_id: Optional[str] = None
    extra: List[str] = Field(default_factory=list)


class Card(BaseModel):
    """Response card following Global LLD envelope structure."""
    status: Literal["ok", "error"]
    type: Literal["card", "overlay_control", "error_card"]
    title: str
    body: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    persisted_ids: PersistedIds = Field(default_factory=PersistedIds)
    diagnostics: Diagnostics
    error_code: Optional[str] = None


# Helper functions for creating standard responses
def ok_card(
    title: str,
    body: str,
    meta: Optional[Dict[str, Any]] = None,
    persisted_ids: Optional[PersistedIds] = None,
    diagnostics: Optional[Diagnostics] = None
) -> Card:
    """Create a successful card response."""
    return Card(
        status="ok",
        type="card",
        title=title,
        body=body,
        meta=meta or {},
        persisted_ids=persisted_ids or PersistedIds(),
        diagnostics=diagnostics or Diagnostics(tool="unknown", duration_ms=0)
    )


def error_card(
    title: str,
    body: str,
    error_code: str,
    tool: str,
    diagnostics: Optional[Diagnostics] = None
) -> Card:
    """Create an error card response."""
    return Card(
        status="error",
        type="error_card",
        title=title,
        body=body,
        meta={"tool": tool, "error_code": error_code},
        diagnostics=diagnostics or Diagnostics(tool=tool, duration_ms=0),
        error_code=error_code
    )


def overlay_control(
    title: str,
    body: str,
    meta: Optional[Dict[str, Any]] = None,
    diagnostics: Optional[Diagnostics] = None
) -> Card:
    """Create an overlay control response."""
    return Card(
        status="ok",
        type="overlay_control",
        title=title,
        body=body,
        meta=meta or {},
        diagnostics=diagnostics or Diagnostics(tool="unknown", duration_ms=0)
    )
