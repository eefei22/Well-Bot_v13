"""
Middleware for fastMCP server following ADD_MCP.md pattern.
Handles auth, envelope validation, error mapping, and timing.
"""

import os
import time
import jwt
import structlog
from typing import Dict, Any, Callable
from .envelopes import MCPRequest, Card, Diagnostics, error_card

logger = structlog.get_logger()


class TimingContext:
    """Context for timing middleware."""
    
    def __init__(self):
        self.start_time = time.time()
    
    def timing(self) -> int:
        """Get elapsed time in milliseconds."""
        return int((time.time() - self.start_time) * 1000)


def timing_mw(handler: Callable) -> Callable:
    """Middleware to track request timing."""
    async def _mw(ctx, req: Dict[str, Any]):
        ctx.timing = TimingContext()
        result = await handler(ctx, req)
        
        # Inject timing into diagnostics if it's a Card
        if isinstance(result, Card):
            result.diagnostics.duration_ms = ctx.timing.timing()
        
        return result
    return _mw


def auth_mw(handler: Callable) -> Callable:
    """Middleware to validate authentication."""
    async def _mw(ctx, req: Dict[str, Any]):
        mode = os.getenv("FASTMCP_AUTH_MODE", "static")
        auth_header = ctx.headers.get("authorization", "")
        token = auth_header.replace("Bearer ", "") if auth_header.startswith("Bearer ") else ""
        
        if mode == "static":
            expected_key = os.getenv("FASTMCP_AUTH_KEY", "dev-secret")
            if token != expected_key:
                logger.warning("Invalid static auth token", tool=ctx.tool)
                return error_card(
                    title="Unauthorized",
                    body="Invalid authentication token",
                    error_code="UNAUTHORIZED",
                    tool=ctx.tool
                )
        else:  # supabase mode
            try:
                # Basic JWT validation (signature verification would require JWKs)
                jwt.decode(token, options={"verify_signature": False})
            except Exception as e:
                logger.warning("Invalid JWT token", tool=ctx.tool, error=str(e))
                return error_card(
                    title="Unauthorized", 
                    body="Invalid JWT token",
                    error_code="UNAUTHORIZED",
                    tool=ctx.tool
                )
        
        return await handler(ctx, req)
    return _mw


def envelope_mw(handler: Callable) -> Callable:
    """Middleware to validate request envelope and ensure Card response."""
    async def _mw(ctx, req: Dict[str, Any]):
        try:
            # Parse and validate MCPRequest
            parsed_req = MCPRequest(**req)
            ctx.req = parsed_req
            
            # Call handler with parsed request
            result = await handler(ctx, parsed_req)
            
            # Ensure response is a Card
            if not isinstance(result, Card):
                logger.error("Handler returned non-Card response", tool=ctx.tool, result_type=type(result))
                return error_card(
                    title="Internal Error",
                    body="Tool returned invalid response format",
                    error_code="INVALID_RESPONSE",
                    tool=ctx.tool
                )
            
            # Inject tool name into diagnostics
            result.diagnostics.tool = ctx.tool
            
            return result
            
        except Exception as e:
            logger.error("Envelope validation failed", tool=ctx.tool, error=str(e))
            return error_card(
                title="Validation Error",
                body="Invalid request format",
                error_code="VALIDATION_ERROR", 
                tool=ctx.tool
            )
    return _mw


def error_mw(handler: Callable) -> Callable:
    """Middleware to map exceptions to error cards."""
    async def _mw(ctx, req: Dict[str, Any]):
        try:
            return await handler(ctx, req)
        except ValueError as e:
            logger.warning("Validation error", tool=ctx.tool, error=str(e))
            return error_card(
                title="Validation Error",
                body=str(e),
                error_code="VALIDATION_ERROR",
                tool=ctx.tool
            )
        except Exception as e:
            logger.error("Unexpected error", tool=ctx.tool, error=str(e), exc_info=True)
            return error_card(
                title="Action Failed",
                body="An unexpected error occurred. Please try again.",
                error_code="UNEXPECTED",
                tool=ctx.tool
            )
    return _mw
