"""
Unit tests for MCP tools infrastructure.
Tests the core envelope handling and tool patterns.
"""

import pytest
import asyncio
from unittest.mock import Mock
from src.backend.mcp_tools.envelopes import MCPRequest, Card, ok_card, error_card
from src.backend.mcp_tools.tools.test_tool import hello


class TestEnvelopes:
    """Test envelope models and helper functions."""
    
    def test_mcp_request_creation(self):
        """Test MCPRequest model creation."""
        req = MCPRequest(
            trace_id="test-123",
            user_id="user-456",
            conversation_id="conv-789",
            session_id="session-abc",
            args={"name": "Alice"},
            ts_utc="2024-01-15T10:30:00Z"
        )
        
        assert req.trace_id == "test-123"
        assert req.user_id == "user-456"
        assert req.args["name"] == "Alice"
    
    def test_ok_card_creation(self):
        """Test ok_card helper function."""
        card = ok_card(
            title="Test Title",
            body="Test Body",
            meta={"kind": "test"}
        )
        
        assert card.status == "ok"
        assert card.type == "card"
        assert card.title == "Test Title"
        assert card.body == "Test Body"
        assert card.meta["kind"] == "test"
    
    def test_error_card_creation(self):
        """Test error_card helper function."""
        card = error_card(
            title="Error Title",
            body="Error Body",
            error_code="TEST_ERROR",
            tool="test.tool"
        )
        
        assert card.status == "error"
        assert card.type == "error_card"
        assert card.error_code == "TEST_ERROR"
        assert card.meta["tool"] == "test.tool"


class TestTestTool:
    """Test the test.hello tool."""
    
    @pytest.mark.asyncio
    async def test_hello_with_name(self):
        """Test hello tool with name parameter."""
        # Mock context
        ctx = Mock()
        ctx.timing.timing.return_value = 50
        
        # Create request
        req = MCPRequest(
            trace_id="test-123",
            user_id="user-456",
            args={"name": "Alice"},
            ts_utc="2024-01-15T10:30:00Z"
        )
        
        # Call tool
        result = await hello(ctx, req)
        
        # Assertions
        assert isinstance(result, Card)
        assert result.status == "ok"
        assert result.title == "Hello"
        assert "Alice" in result.body
        assert result.diagnostics.tool == "test.hello"
        assert result.diagnostics.duration_ms == 50
    
    @pytest.mark.asyncio
    async def test_hello_without_name(self):
        """Test hello tool without name parameter."""
        # Mock context
        ctx = Mock()
        ctx.timing.timing.return_value = 25
        
        # Create request
        req = MCPRequest(
            trace_id="test-123",
            user_id="user-456",
            args={},
            ts_utc="2024-01-15T10:30:00Z"
        )
        
        # Call tool
        result = await hello(ctx, req)
        
        # Assertions
        assert isinstance(result, Card)
        assert result.status == "ok"
        assert result.title == "Hello"
        assert "friend" in result.body
        assert result.diagnostics.tool == "test.hello"


if __name__ == "__main__":
    pytest.main([__file__])
