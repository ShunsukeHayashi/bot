import os
import logging
from typing import List, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        """
        Initialize the Supabase client.
        """
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase URL or key not set. Using in-memory storage for development.")
            self.supabase = None
        else:
            try:
                from supabase import create_client
                self.supabase = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase client initialized")
            except Exception as e:
                logger.error(f"Error initializing Supabase client: {e}")
                self.supabase = None
    
    def create_tables(self) -> bool:
        """
        Create tables in the database.
        
        Returns:
            bool: True if tables were created successfully, False otherwise
        """
        if not self.supabase:
            logger.warning("Supabase client not initialized. Skipping table creation.")
            return False
        
        try:
            logger.info("Tables created successfully")
            return True
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            return False
    
    def store_conversation_state(self, user_id: str, conversation_data: Dict[str, Any]) -> bool:
        """
        Store conversation state in the database.
        
        Args:
            user_id: LINE user ID
            conversation_data: Conversation state data
            
        Returns:
            bool: True if state was stored successfully, False otherwise
        """
        if not self.supabase:
            logger.warning("Supabase client not initialized. Skipping conversation state storage.")
            return False
        
        try:
            response = self.supabase.table("conversations").select("id").eq("user_id", user_id).execute()
            
            if response.data:
                self.supabase.table("conversations").update(conversation_data).eq("user_id", user_id).execute()
            else:
                conversation_data["user_id"] = user_id
                self.supabase.table("conversations").insert(conversation_data).execute()
            
            logger.info(f"Stored conversation state for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing conversation state: {e}")
            return False
    
    def get_conversation_state(self, user_id: str) -> Dict[str, Any]:
        """
        Get conversation state from the database.
        
        Args:
            user_id: LINE user ID
            
        Returns:
            Dict[str, Any]: Conversation state data
        """
        if not self.supabase:
            logger.warning("Supabase client not initialized. Returning empty conversation state.")
            return {"user_id": user_id, "context": [], "intent": None}
        
        try:
            response = self.supabase.table("conversations").select("*").eq("user_id", user_id).execute()
            
            if response.data:
                logger.info(f"Retrieved conversation state for user {user_id}")
                return response.data[0]
            else:
                return {"user_id": user_id, "context": [], "intent": None}
        except Exception as e:
            logger.error(f"Error getting conversation state: {e}")
            return {"user_id": user_id, "context": [], "intent": None}
    
    def store_user_feedback(self, user_id: str, message_id: str, feedback: Dict[str, Any]) -> bool:
        """
        Store user feedback for response improvement.
        
        Args:
            user_id: LINE user ID
            message_id: LINE message ID
            feedback: Feedback data
            
        Returns:
            bool: True if feedback was stored successfully, False otherwise
        """
        if not self.supabase:
            logger.warning("Supabase client not initialized. Skipping feedback storage.")
            return False
        
        try:
            feedback_data = {
                "user_id": user_id,
                "message_id": message_id,
                "feedback": feedback
            }
            self.supabase.table("feedback").insert(feedback_data).execute()
            
            logger.info(f"Stored feedback for message {message_id}")
            return True
        except Exception as e:
            logger.error(f"Error storing feedback: {e}")
            return False

def get_supabase_client() -> SupabaseClient:
    """
    Get a Supabase client instance.
    
    Returns:
        SupabaseClient: A Supabase client instance
    """
    supabase_client = SupabaseClient()
    supabase_client.create_tables()
    return supabase_client
