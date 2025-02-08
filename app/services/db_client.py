from typing import Optional
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class DBClient:
    _instance: Optional['DBClient'] = None
    _client: Optional[Client] = None

    def __init__(self):
        """Initialize Supabase client with environment variables"""
        if DBClient._instance is not None:
            raise Exception("DBClient is a singleton. Use get_instance() instead.")
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
        
        try:
            self._client = create_client(url, key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {str(e)}")
            raise

    @classmethod
    def get_instance(cls) -> 'DBClient':
        """Get singleton instance of DBClient"""
        if cls._instance is None:
            cls._instance = DBClient()
        return cls._instance

    @property
    def client(self) -> Client:
        """Get the Supabase client"""
        if self._client is None:
            raise Exception("Supabase client not initialized")
        return self._client

    async def execute_query(self, query: str, *args, **kwargs) -> dict:
        """Execute a raw SQL query"""
        try:
            result = await self.client.rpc(
                'execute_sql',
                {'query': query, 'params': args}
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

# Initialize singleton instance
db = DBClient.get_instance()