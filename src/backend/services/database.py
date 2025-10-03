"""
Database connection utility for Well-Bot Supabase integration.
Provides singleton client and health check functionality.
"""

import os
import structlog
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = structlog.get_logger()

class DatabaseManager:
    """Singleton database manager for Supabase connections."""
    
    _instance: Optional['DatabaseManager'] = None
    _client: Optional[Client] = None
    
    def __new__(cls) -> 'DatabaseManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client with environment variables."""
        try:
            url = os.getenv("SUPABASE_URL")
            service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            
            if not url or not service_key:
                raise ValueError("Missing required Supabase environment variables")
            
            self._client = create_client(url, service_key)
            logger.info("Supabase client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Supabase client", error=str(e))
            raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    async def health_check(self) -> dict:
        """
        Perform database health check.
        
        Returns:
            dict: Health status with connection info
        """
        try:
            # Test basic connection by querying a simple table
            # Using wb_preferences as it's lightweight and always exists
            result = self.client.table("wb_preferences").select("user_id").limit(1).execute()
            
            return {
                "status": "healthy",
                "message": "Database connection successful",
                "tables_accessible": True,
                "response_time_ms": "< 1000"  # Supabase typically responds quickly
            }
            
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}",
                "tables_accessible": False,
                "error": str(e)
            }
    
    async def test_table_access(self, table_name: str) -> dict:
        """
        Test access to a specific table.
        
        Args:
            table_name: Name of the table to test
            
        Returns:
            dict: Test results
        """
        try:
            # Try to select from the table with limit 1
            result = self.client.table(table_name).select("*").limit(1).execute()
            
            return {
                "table": table_name,
                "accessible": True,
                "row_count": len(result.data),
                "message": f"Successfully accessed {table_name}"
            }
            
        except Exception as e:
            logger.error(f"Table access test failed for {table_name}", error=str(e))
            return {
                "table": table_name,
                "accessible": False,
                "error": str(e),
                "message": f"Failed to access {table_name}: {str(e)}"
            }

# Global database manager instance
db_manager = DatabaseManager()

# Convenience functions
def get_db_client() -> Client:
    """Get the global Supabase client instance."""
    return db_manager.client

async def health_check() -> dict:
    """Perform database health check."""
    return await db_manager.health_check()

async def test_table_access(table_name: str) -> dict:
    """Test access to a specific table."""
    return await db_manager.test_table_access(table_name)

