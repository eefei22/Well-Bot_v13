#!/usr/bin/env python3
"""
Simple test script to verify DeepSeek LLM integration.
Tests the /llm/chat:turn endpoint with various inputs.
"""

import asyncio
import httpx
import json
import time
from typing import Dict, Any


async def test_chat_turn(client: httpx.AsyncClient, text: str, expected_type: str = "card") -> Dict[str, Any]:
    """Test a single chat turn and return the response."""
    request = {
        "text": text,
        "user_id": "test-user-123",
        "conversation_id": "test-conv-456",
        "session_id": "test-session-789",
        "trace_id": f"test-{int(time.time())}"
    }
    
    print(f"\n🧪 Testing: '{text}'")
    start_time = time.time()
    
    try:
        response = await client.post("/llm/chat:turn", json=request)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success ({duration:.2f}s)")
            print(f"   Status: {data['status']}")
            print(f"   Type: {data['type']}")
            print(f"   Title: {data['title']}")
            print(f"   Body: {data['body'][:100]}{'...' if len(data['body']) > 100 else ''}")
            print(f"   Meta: {data['meta']}")
            print(f"   Duration: {data['diagnostics']['duration_ms']}ms")
            return data
        else:
            print(f"❌ Failed ({duration:.2f}s)")
            print(f"   Status: {response.status_code}")
            print(f"   Error: {response.text}")
            return {}
            
    except Exception as e:
        duration = time.time() - start_time
        print(f"❌ Exception ({duration:.2f}s): {e}")
        return {}


async def main():
    """Run comprehensive tests of the LLM chat turn endpoint."""
    print("🚀 Testing DeepSeek LLM Integration")
    print("=" * 50)
    
    async with httpx.AsyncClient(base_url="http://localhost:8080") as client:
        # Test cases covering different scenarios
        test_cases = [
            # Small talk
            ("Hello, how are you?", "small_talk"),
            ("What's the weather like?", "small_talk"),
            ("I'm feeling stressed today", "small_talk"),
            
            # Tool intents (should return stub cards)
            ("show my to-do list", "todo.list"),
            ("start journal", "journal.start"),
            ("add to-do buy groceries", "todo.add"),
            ("give me a quote", "quote.get"),
            ("start meditation", "meditation.play"),
            ("bye", "session.end"),
            
            # Safety triggers (should return support card)
            ("I want to hurt myself", "safety"),
            ("I'm thinking about suicide", "safety"),
        ]
        
        results = []
        
        for text, expected_type in test_cases:
            result = await test_chat_turn(client, text, expected_type)
            results.append({
                "text": text,
                "expected": expected_type,
                "success": result.get("status") == "ok",
                "duration": result.get("diagnostics", {}).get("duration_ms", 0)
            })
            
            # Small delay between requests
            await asyncio.sleep(0.5)
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        successful = sum(1 for r in results if r["success"])
        total = len(results)
        avg_duration = sum(r["duration"] for r in results) / total if total > 0 else 0
        
        print(f"✅ Successful: {successful}/{total}")
        print(f"⏱️  Average Duration: {avg_duration:.0f}ms")
        print(f"🎯 Success Rate: {(successful/total)*100:.1f}%")
        
        # Check performance budget
        slow_tests = [r for r in results if r["duration"] > 5000]  # 5s budget
        if slow_tests:
            print(f"⚠️  Slow tests: {len(slow_tests)}")
            for test in slow_tests:
                print(f"   - '{test['text']}': {test['duration']}ms")
        else:
            print("✅ All tests within 5s budget")
        
        # Check for failures
        failed_tests = [r for r in results if not r["success"]]
        if failed_tests:
            print(f"❌ Failed tests: {len(failed_tests)}")
            for test in failed_tests:
                print(f"   - '{test['text']}'")
        else:
            print("✅ All tests passed")


if __name__ == "__main__":
    print("Make sure the FastAPI server is running on http://localhost:8080")
    print("You can start it with: python -m src.backend.api.main")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
