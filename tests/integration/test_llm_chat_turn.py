"""
Integration tests for LLM chat turn pipeline.
Tests the complete flow: safety → intent → LLM/stub with comprehensive coverage.
Automatically starts server and installs dependencies.
"""

import pytest
import httpx
import asyncio
import time
import subprocess
import sys
import os
import signal
from typing import Dict, Any
from pathlib import Path


class TestLLMChatTurn:
    """Test suite for /llm/chat:turn endpoint."""
    
    @pytest.fixture(scope="session")
    def server_process(self):
        """Start the FastAPI server for testing."""
        print("\n🚀 Starting FastAPI server for testing...")
        
        # Install missing dependencies
        try:
            import openai
        except ImportError:
            print("📦 Installing missing dependencies...")
            subprocess.run([sys.executable, "-m", "pip", "install", "openai"], check=True)
        
        # Start server
        server_cmd = [sys.executable, "-m", "src.backend.api.main"]
        process = subprocess.Popen(
            server_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent.parent
        )
        
        # Wait for server to start
        print("⏳ Waiting for server to start...")
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = httpx.get("http://localhost:8080/healthz", timeout=1.0)
                if response.status_code == 200:
                    print("✅ Server started successfully!")
                    break
            except:
                time.sleep(1)
        else:
            # Server didn't start, get error output
            stdout, stderr = process.communicate()
            print(f"❌ Server failed to start:")
            print(f"STDOUT: {stdout.decode()}")
            print(f"STDERR: {stderr.decode()}")
            process.terminate()
            pytest.fail("Server failed to start")
        
        yield process
        
        # Cleanup
        print("\n🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Server stopped")
    
    @pytest.fixture
    async def client(self):
        """Create async HTTP client for testing."""
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            yield client
    
    @pytest.fixture
    def base_request(self) -> Dict[str, Any]:
        """Base request payload for chat turn."""
        return {
            "text": "Hello, how are you?",
            "user_id": "test-user-123",
            "conversation_id": "test-conv-456",
            "session_id": "test-session-789",
            "trace_id": "test-trace-001"
        }
    
    async def test_small_talk_response(self, client, base_request):
        """Test 1: Small-talk utterance → verify ok card with chat response."""
        base_request["text"] = "Hello, how are you doing today?"
        
        start_time = time.time()
        response = await client.post("/llm/chat/turn", json=base_request)
        duration = time.time() - start_time
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response envelope structure
        assert data["status"] == "ok"
        assert data["type"] == "card"
        assert "title" in data
        assert "body" in data
        assert "meta" in data
        assert "diagnostics" in data
        
        # Verify diagnostics
        diagnostics = data["diagnostics"]
        assert diagnostics["tool"] == "llm.chat_turn"
        assert diagnostics["duration_ms"] > 0
        assert duration < 5.0  # <5s per LLD
        
        # Verify meta
        assert data["meta"]["kind"] == "info"
        
        # Verify response contains actual content
        assert len(data["body"]) > 0
        assert data["title"] == "Chat Response"
    
    async def test_tool_intent_stub_card(self, client, base_request):
        """Test 2: Tool intent ("show my to-do list") → verify stub card."""
        base_request["text"] = "show my to-do list"
        
        response = await client.post("/llm/chat/turn", json=base_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify stub card structure
        assert data["status"] == "ok"
        assert data["type"] == "card"
        assert data["title"] == "Your To-Dos"
        assert "(stub)" in data["body"]
        assert data["meta"]["kind"] == "todo"
        
        # Verify diagnostics
        assert data["diagnostics"]["tool"] == "llm.chat_turn"
        assert data["diagnostics"]["duration_ms"] > 0
    
    async def test_safety_trigger_support_card(self, client, base_request):
        """Test 3: Safety trigger phrase → verify support card (no LLM call)."""
        base_request["text"] = "I want to hurt myself"
        
        response = await client.post("/llm/chat/turn", json=base_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify support card
        assert data["status"] == "ok"
        assert data["type"] == "card"
        assert "Support" in data["title"]
        assert "support" in data["body"].lower()
        
        # Verify diagnostics
        assert data["diagnostics"]["tool"] == "llm.chat_turn"
        assert data["diagnostics"]["duration_ms"] > 0
    
    async def test_response_envelope_structure(self, client, base_request):
        """Test 4: Verify response envelope structure (status, type, title, body, meta, diagnostics)."""
        response = await client.post("/llm/chat/turn", json=base_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Required fields
        required_fields = ["status", "type", "title", "body", "meta", "diagnostics"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Status must be "ok" or "error"
        assert data["status"] in ["ok", "error"]
        
        # Type must be valid card type
        assert data["type"] in ["card", "overlay_control", "error_card"]
        
        # Meta must be dict
        assert isinstance(data["meta"], dict)
        
        # Diagnostics must have required fields
        diagnostics = data["diagnostics"]
        assert "tool" in diagnostics
        assert "duration_ms" in diagnostics
        assert isinstance(diagnostics["duration_ms"], int)
    
    async def test_intent_classifier_matrix(self, client, base_request):
        """Test 6: Intent classifier matrix (small-talk, todo.list, journal.start, quote.get, meditation.play, session.end, ambiguous line)."""
        
        test_cases = [
            {
                "text": "Hello, how are you?",
                "expected_intent": "small_talk",
                "expected_title": "Chat Response",
                "expected_kind": "info"
            },
            {
                "text": "show my to-do list",
                "expected_intent": "todo.list",
                "expected_title": "Your To-Dos",
                "expected_kind": "todo"
            },
            {
                "text": "start journal",
                "expected_intent": "journal.start",
                "expected_title": "Journal Session",
                "expected_kind": "journal"
            },
            {
                "text": "give me a quote",
                "expected_intent": "quote.get",
                "expected_title": "Spiritual Quote",
                "expected_kind": "quote"
            },
            {
                "text": "start meditation",
                "expected_intent": "meditation.play",
                "expected_title": "Meditation Starting",
                "expected_kind": "meditation"
            },
            {
                "text": "bye",
                "expected_intent": "session.end",
                "expected_title": "Session Ending",
                "expected_kind": "info"
            },
            {
                "text": "I'm feeling overwhelmed and need some guidance",
                "expected_intent": "small_talk",  # Ambiguous - should fallback to small_talk
                "expected_title": "Chat Response",
                "expected_kind": "info"
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            base_request["text"] = test_case["text"]
            base_request["trace_id"] = f"test-matrix-{i}"
            
            response = await client.post("/llm/chat/turn", json=base_request)
            
            assert response.status_code == 200, f"Failed for test case {i}: {test_case['text']}"
            data = response.json()
            
            # Verify expected structure
            assert data["status"] == "ok"
            assert data["type"] == "card"
            
            # For stub cards, verify they have "(stub)" marker
            if test_case["expected_kind"] != "info" or test_case["expected_title"] != "Chat Response":
                assert "(stub)" in data["body"]
            
            # Verify meta kind
            assert data["meta"]["kind"] == test_case["expected_kind"]
    
    async def test_stub_cards_consistency(self, client, base_request):
        """Test that all stub cards have consistent structure and (stub) markers."""
        
        stub_intents = [
            ("start journal", "journal"),
            ("add to-do buy groceries", "todo"),
            ("show my to-do list", "todo"),
            ("give me a quote", "quote"),
            ("start meditation", "meditation"),
            ("bye", "info")
        ]
        
        for text, expected_kind in stub_intents:
            base_request["text"] = text
            
            response = await client.post("/llm/chat/turn", json=base_request)
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify stub marker
            assert "(stub)" in data["body"], f"Missing (stub) marker for: {text}"
            
            # Verify meta kind
            assert data["meta"]["kind"] == expected_kind, f"Wrong meta.kind for: {text}"
            
            # Verify response structure
            assert data["status"] == "ok"
            assert data["type"] == "card"
            assert len(data["title"]) > 0
            assert len(data["body"]) > 0
    
    async def test_error_handling(self, client):
        """Test error handling with invalid requests."""
        
        # Test missing required fields
        invalid_request = {"text": "test"}
        
        response = await client.post("/llm/chat:turn", json=invalid_request)
        
        # Should return 422 for validation error
        assert response.status_code == 422
    
    async def test_performance_budget(self, client, base_request):
        """Test that responses complete within 5s budget."""
        
        test_texts = [
            "Hello, how are you?",
            "show my to-do list",
            "start journal",
            "give me a quote",
            "start meditation"
        ]
        
        for text in test_texts:
            base_request["text"] = text
            
            start_time = time.time()
            response = await client.post("/llm/chat/turn", json=base_request)
            duration = time.time() - start_time
            
            assert response.status_code == 200
            assert duration < 5.0, f"Response too slow for: {text} ({duration:.2f}s)"
            
            # Also verify diagnostics duration
            data = response.json()
            diagnostics_duration = data["diagnostics"]["duration_ms"] / 1000.0
            assert diagnostics_duration < 5.0, f"Diagnostics duration too slow: {diagnostics_duration:.2f}s"


# Run tests with: pytest tests/integration/test_llm_chat_turn.py -v


async def run_standalone_test():
    """Run a standalone test without pytest - useful for quick verification."""
    print("🧪 Running standalone LLM chat turn test...")
    
    # Install dependencies if needed
    try:
        import openai
    except ImportError:
        print("📦 Installing missing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai"], check=True)
    
    # Start server
    print("🚀 Starting server...")
    server_cmd = [sys.executable, "-m", "src.backend.api.main"]
    process = subprocess.Popen(
        server_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent.parent
    )
    
    try:
        # Wait for server
        print("⏳ Waiting for server to start...")
        for i in range(30):
            try:
                response = httpx.get("http://localhost:8080/healthz", timeout=1.0)
                if response.status_code == 200:
                    print("✅ Server started!")
                    break
            except:
                time.sleep(1)
        else:
            raise Exception("Server failed to start")
        
        # Run tests
        async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
            test_cases = [
                ("Hello, how are you?", "small_talk"),
                ("show my to-do list", "todo.list"),
                ("start journal", "journal.start"),
                ("give me a quote", "quote.get"),
                ("start meditation", "meditation.play"),
                ("bye", "session.end"),
            ]
            
            print("\n🧪 Running test cases...")
            for i, (text, expected_type) in enumerate(test_cases):
                print(f"\n{i+1}. Testing: '{text}'")
                
                request = {
                    "text": text,
                    "user_id": "test-user-123",
                    "conversation_id": "test-conv-456",
                    "session_id": "test-session-789",
                    "trace_id": f"standalone-test-{i}"
                }
                
                start_time = time.time()
                try:
                    response = await client.post("/llm/chat/turn", json=request)
                    duration = time.time() - start_time
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"   ✅ Success ({duration:.2f}s)")
                        print(f"   Status: {data['status']}")
                        print(f"   Type: {data['type']}")
                        print(f"   Title: {data['title']}")
                        print(f"   Body: {data['body'][:80]}{'...' if len(data['body']) > 80 else ''}")
                        print(f"   Meta: {data['meta']}")
                        print(f"   Duration: {data['diagnostics']['duration_ms']}ms")
                    else:
                        print(f"   ❌ Failed ({duration:.2f}s): {response.status_code}")
                        print(f"   Error: {response.text}")
                        
                except Exception as e:
                    duration = time.time() - start_time
                    print(f"   ❌ Exception ({duration:.2f}s): {e}")
                
                await asyncio.sleep(0.5)  # Small delay between requests
        
        print("\n✅ Standalone test completed!")
        
    finally:
        # Cleanup
        print("\n🛑 Stopping server...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("✅ Server stopped")


if __name__ == "__main__":
    """Run standalone test when executed directly."""
    print("🚀 Starting LLM Chat Turn Integration Test")
    print("=" * 50)
    print("This will:")
    print("1. Install missing dependencies (if needed)")
    print("2. Start the FastAPI server")
    print("3. Run test cases against /llm/chat:turn")
    print("4. Stop the server")
    print("=" * 50)
    
    try:
        asyncio.run(run_standalone_test())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
