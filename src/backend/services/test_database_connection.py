"""
Database connection health test for Well-Bot.
Tests Supabase connectivity and table access.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.database import db_manager, health_check, test_table_access
import structlog

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Tables from Schema.sql to test
TEST_TABLES = [
    "wb_preferences",
    "wb_journal", 
    "wb_todo_item",
    "wb_gratitude_item",
    "wb_quote",
    "wb_meditation_video",
    "wb_conversation",
    "wb_message",
    "wb_session_log",
    "wb_safety_event",
    "wb_tool_invocation_log",
    "wb_embeddings",
    "wb_meditation_log",
    "wb_quote_seen",
    "wb_activity_event"
]

async def run_comprehensive_test():
    """Run comprehensive database connectivity tests."""
    print("Well-Bot Database Connection Test")
    print("=" * 50)
    
    # Test 1: Basic health check
    print("\n1. Basic Health Check")
    print("-" * 30)
    health_result = await health_check()
    
    if health_result["status"] == "healthy":
        print("[OK] Database connection: HEALTHY")
        print(f"   Message: {health_result['message']}")
    else:
        print("[ERROR] Database connection: UNHEALTHY")
        print(f"   Error: {health_result['message']}")
        return False
    
    # Test 2: Table access tests
    print("\n2. Table Access Tests")
    print("-" * 30)
    
    accessible_tables = []
    inaccessible_tables = []
    
    for table in TEST_TABLES:
        result = await test_table_access(table)
        if result["accessible"]:
            accessible_tables.append(table)
            print(f"[OK] {table}: Accessible")
        else:
            inaccessible_tables.append(table)
            print(f"[ERROR] {table}: {result['error']}")
    
    # Test 3: Summary
    print("\n3. Test Summary")
    print("-" * 30)
    print(f"Total tables tested: {len(TEST_TABLES)}")
    print(f"Accessible tables: {len(accessible_tables)}")
    print(f"Inaccessible tables: {len(inaccessible_tables)}")
    
    if inaccessible_tables:
        print(f"\nInaccessible tables: {', '.join(inaccessible_tables)}")
    
    # Test 4: Environment variables check
    print("\n4. Environment Variables Check")
    print("-" * 30)
    
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the key for security
            if "KEY" in var:
                masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"[OK] {var}: {masked_value}")
            else:
                print(f"[OK] {var}: {value}")
        else:
            missing_vars.append(var)
            print(f"[ERROR] {var}: Not set")
    
    if missing_vars:
        print(f"\nMissing environment variables: {', '.join(missing_vars)}")
        return False
    
    # Final result
    print("\n" + "=" * 50)
    if len(inaccessible_tables) == 0 and len(missing_vars) == 0:
        print("[SUCCESS] ALL TESTS PASSED - Database integration is healthy!")
        return True
    else:
        print("[WARNING] SOME TESTS FAILED - Check the issues above")
        return False

async def quick_test():
    """Run a quick database connectivity test."""
    print("Quick Database Test")
    print("-" * 30)
    
    try:
        result = await health_check()
        if result["status"] == "healthy":
            print("[OK] Database connection: HEALTHY")
            return True
        else:
            print(f"[ERROR] Database connection: {result['message']}")
            return False
    except Exception as e:
        print(f"[ERROR] Database test failed: {str(e)}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Well-Bot database connection")
    parser.add_argument("--quick", action="store_true", help="Run quick test only")
    args = parser.parse_args()
    
    try:
        if args.quick:
            success = asyncio.run(quick_test())
        else:
            success = asyncio.run(run_comprehensive_test())
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nTest failed with error: {str(e)}")
        sys.exit(1)
