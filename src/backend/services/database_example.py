"""
Example usage of the Well-Bot database integration.
Shows how to use the database manager in MCP tools.
"""

import asyncio
import sys
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.database import get_db_client, health_check, test_table_access

async def example_usage():
    """Example of how to use the database integration in MCP tools."""
    
    print("Well-Bot Database Integration Example")
    print("=" * 50)
    
    # Get the Supabase client
    client = get_db_client()
    print("[OK] Database client obtained")
    
    # Example 1: Insert a test journal entry
    print("\n1. Example: Insert Journal Entry")
    print("-" * 30)
    
    try:
        # This would be used in journal_tool.py
        journal_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",  # Test user ID
            "title": "Test Journal Entry",
            "body": "This is a test journal entry created during database integration testing.",
            "mood": 3,
            "topics": ["testing", "integration"],
            "is_draft": False
        }
        
        result = client.table("wb_journal").insert(journal_data).execute()
        print(f"[OK] Journal entry created with ID: {result.data[0]['id']}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create journal entry: {str(e)}")
    
    # Example 2: Query journal entries
    print("\n2. Example: Query Journal Entries")
    print("-" * 30)
    
    try:
        # This would be used in journal_tool.py for listing entries
        result = client.table("wb_journal").select("*").limit(5).execute()
        print(f"[OK] Found {len(result.data)} journal entries")
        
        for entry in result.data:
            print(f"   - {entry['title']} (mood: {entry['mood']})")
            
    except Exception as e:
        print(f"[ERROR] Failed to query journal entries: {str(e)}")
    
    # Example 3: Insert a todo item
    print("\n3. Example: Insert Todo Item")
    print("-" * 30)
    
    try:
        # This would be used in todo_tool.py
        todo_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",  # Test user ID
            "title": "Test Database Integration",
            "status": "open"
        }
        
        result = client.table("wb_todo_item").insert(todo_data).execute()
        print(f"[OK] Todo item created with ID: {result.data[0]['id']}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create todo item: {str(e)}")
    
    # Example 4: Update todo status
    print("\n4. Example: Update Todo Status")
    print("-" * 30)
    
    try:
        # This would be used in todo_tool.py for completing todos
        if 'result' in locals() and result.data:
            todo_id = result.data[0]['id']
            update_result = client.table("wb_todo_item").update({
                "status": "completed",
                "completed_at": "now()"
            }).eq("id", todo_id).execute()
            
            print(f"[OK] Todo item {todo_id} marked as completed")
        
    except Exception as e:
        print(f"[ERROR] Failed to update todo status: {str(e)}")
    
    # Example 5: Insert gratitude item
    print("\n5. Example: Insert Gratitude Item")
    print("-" * 30)
    
    try:
        # This would be used in gratitude_tool.py
        gratitude_data = {
            "user_id": "00000000-0000-0000-0000-000000000000",  # Test user ID
            "text": "Grateful for successful database integration!"
        }
        
        result = client.table("wb_gratitude_item").insert(gratitude_data).execute()
        print(f"[OK] Gratitude item created with ID: {result.data[0]['id']}")
        
    except Exception as e:
        print(f"[ERROR] Failed to create gratitude item: {str(e)}")
    
    print("\n" + "=" * 50)
    print("[SUCCESS] Database integration examples completed!")
    print("\nNext steps:")
    print("1. Update MCP tools to use get_db_client()")
    print("2. Replace mock data with real database operations")
    print("3. Add proper error handling and logging")
    print("4. Implement user authentication and authorization")

if __name__ == "__main__":
    try:
        asyncio.run(example_usage())
    except KeyboardInterrupt:
        print("\n\nExample interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nExample failed with error: {str(e)}")
        sys.exit(1)
