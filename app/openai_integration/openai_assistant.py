import os
import logging
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

class OpenAIAssistant:
    """
    OpenAI Assistant client for processing messages using the Assistants API.
    
    This class provides a client for interacting with the OpenAI Assistants API,
    allowing for creation and management of assistants, threads, and messages.
    """
    
    def __init__(self, api_key: Optional[str] = None, assistant_id: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the OpenAI Assistant client.
        
        Args:
            api_key: OpenAI API key
            assistant_id: Existing assistant ID to use
            model: Model to use for new assistants
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.assistant_id = assistant_id or os.getenv("OPENAI_ASSISTANT_ID")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4-turbo")
        self.is_available = False
        
        if not self.api_key:
            logger.warning("OpenAI API key not set. API calls will not work.")
            self.client = None
        else:
            try:
                self.client = OpenAI(api_key=self.api_key)
                self.client.models.list()
                self.is_available = True
                
                if not self.assistant_id and self.client:
                    self.assistant_id = self._create_default_assistant()
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {e}")
                self.client = None
                self.is_available = False
        
        logger.info(f"OpenAI Assistant client initialized. Available: {self.is_available}")
    
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message using the OpenAI Assistant.
        
        Args:
            message: User message
            user_id: User identifier
            conversation_state: Current conversation state
            
        Returns:
            Dict[str, Any]: Response including message and updated conversation state
        """
        if not self.is_available or not self.client or not self.assistant_id:
            logger.warning("OpenAI Assistant not properly configured. Returning fallback message.")
            return {
                "message": "申し訳ありませんが、現在OpenAI Assistantは利用できません。別の方法でお手伝いします。",
                "conversation_state": conversation_state
            }
        
        try:
            thread_id = conversation_state.get("openai_thread_id")
            if not thread_id:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
            
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message
            )
            
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id
            )
            
            run = self._wait_for_run(thread_id, run.id)
            
            if run.status != "completed":
                logger.warning(f"Run did not complete successfully: {run.status}")
                return {
                    "message": "申し訳ありません、応答の生成中にエラーが発生しました。",
                    "conversation_state": {
                        **conversation_state,
                        "openai_thread_id": thread_id
                    }
                }
            
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            if not messages.data:
                return {
                    "message": "応答が見つかりませんでした。",
                    "conversation_state": {
                        **conversation_state,
                        "openai_thread_id": thread_id
                    }
                }
            
            assistant_message = messages.data[0]
            response_content = assistant_message.content[0].text.value if assistant_message.content else "応答がありませんでした。"
            
            updated_state = {
                **conversation_state,
                "openai_thread_id": thread_id
            }
            
            return {
                "message": response_content,
                "conversation_state": updated_state
            }
        except Exception as e:
            logger.error(f"Error processing message with OpenAI Assistant: {e}")
            return {
                "message": "OpenAI Assistantとの通信中にエラーが発生しました。",
                "conversation_state": conversation_state
            }
    
    def _wait_for_run(self, thread_id: str, run_id: str) -> Any:
        """Wait for a run to complete."""
        import time
        
        while True:
            run = self.client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run_id
            )
            
            if run.status in ["completed", "failed", "cancelled", "expired"]:
                return run
            
            time.sleep(1)
    
    def _create_default_assistant(self) -> Optional[str]:
        """Create a default assistant."""
        if not self.is_available:
            return None
            
        try:
            assistant = self.client.beta.assistants.create(
                name="テレグラムボット用アシスタント",
                instructions="ユーザーの質問に日本語で回答し、役立つ情報を提供します。",
                model=self.model,
                tools=[{"type": "code_interpreter"}]
            )
            
            logger.info(f"Created default assistant with ID: {assistant.id}")
            return assistant.id
        except Exception as e:
            logger.error(f"Error creating default assistant: {e}")
            return None
    
    def create_assistant(self, name: str, instructions: str, model: Optional[str] = None) -> Optional[str]:
        """Create a new assistant."""
        if not self.is_available:
            return None
            
        try:
            assistant = self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model or self.model,
                tools=[{"type": "code_interpreter"}]
            )
            
            return assistant.id
        except Exception as e:
            logger.error(f"Error creating assistant: {e}")
            return None
    
    def get_assistant(self, assistant_id: str) -> Dict[str, Any]:
        """Get assistant details."""
        if not self.is_available:
            return {}
            
        try:
            assistant = self.client.beta.assistants.retrieve(assistant_id=assistant_id)
            return assistant.model_dump()
        except Exception as e:
            logger.error(f"Error retrieving assistant: {e}")
            return {}
    
    def list_assistants(self) -> List[Dict[str, Any]]:
        """List all assistants."""
        if not self.is_available:
            return []
            
        try:
            assistants = self.client.beta.assistants.list()
            return [a.model_dump() for a in assistants.data]
        except Exception as e:
            logger.error(f"Error listing assistants: {e}")
            return []
    
    def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        if not self.is_available:
            return False
            
        try:
            self.client.beta.assistants.delete(assistant_id=assistant_id)
            return True
        except Exception as e:
            logger.error(f"Error deleting assistant: {e}")
            return False

def get_openai_assistant() -> OpenAIAssistant:
    """
    Get an OpenAI Assistant instance.
    
    Returns:
        OpenAIAssistant: An OpenAI Assistant instance
    """
    return OpenAIAssistant()
