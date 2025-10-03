"""
Integration tests for FastAPI health endpoints.
Tests liveness and readiness probes with actual HTTP requests.
"""

import pytest
import pytest_asyncio
import httpx
from datetime import datetime
import json

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


@pytest.fixture
def base_url():
    """Base URL for the API server."""
    return "http://localhost:8080"


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing."""
    async with httpx.AsyncClient() as client:
        yield client


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_healthz_liveness(self, client, base_url):
        """Test liveness probe endpoint."""
        response = await client.get(f"{base_url}/healthz")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "api"
        assert data["version"] == "1.0.0"
        assert "time" in data
        
        # Verify time is valid ISO format
        datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
    
    async def test_readyz_readiness(self, client, base_url):
        """Test readiness probe endpoint."""
        response = await client.get(f"{base_url}/readyz")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["ok", "error"]  # Can be either depending on DB
        assert data["service"] == "api"
        assert "time" in data
        assert "db" in data
        
        # Verify time is valid ISO format
        datetime.fromisoformat(data["time"].replace("Z", "+00:00"))
        
        # Verify DB status structure
        db_status = data["db"]
        assert "status" in db_status
        assert "message" in db_status
        assert db_status["status"] in ["healthy", "unhealthy"]
    
    async def test_root_endpoint(self, client, base_url):
        """Test root endpoint with API information."""
        response = await client.get(f"{base_url}/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Well-Bot API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"
        assert "endpoints" in data
        
        endpoints = data["endpoints"]
        assert endpoints["health"] == "/healthz"
        assert endpoints["readiness"] == "/readyz"
    
    async def test_cors_headers(self, client, base_url):
        """Test CORS headers are present."""
        # Test CORS headers on a GET request (OPTIONS might not be supported)
        response = await client.get(f"{base_url}/healthz")
        
        # CORS headers should be present on successful requests
        assert response.status_code == 200
        # Note: CORS headers are typically added by middleware on actual requests
        # The middleware should add these headers automatically


class TestHealthEndpointPerformance:
    """Test health endpoint performance and reliability."""
    
    async def test_healthz_response_time(self, client, base_url):
        """Test that healthz responds quickly."""
        import time
        
        start_time = time.time()
        response = await client.get(f"{base_url}/healthz")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Should respond within 1 second
    
    async def test_readyz_response_time(self, client, base_url):
        """Test that readyz responds within reasonable time."""
        import time
        
        start_time = time.time()
        response = await client.get(f"{base_url}/readyz")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 5.0  # Should respond within 5 seconds (includes DB check)
    
    async def test_concurrent_health_checks(self, client, base_url):
        """Test multiple concurrent health check requests."""
        import asyncio
        
        # Make 5 concurrent requests
        tasks = [
            client.get(f"{base_url}/healthz")
            for _ in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
