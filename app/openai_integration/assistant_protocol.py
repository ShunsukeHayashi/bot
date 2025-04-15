import logging
from typing import Dict, Any, List, Optional, Protocol

logger = logging.getLogger(__name__)

class AssistantProtocol(Protocol):
    """Protocol for assistant components."""
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response."""
        ...
    
    def create_assistant(self, name: str, instructions: str, model: str) -> str:
        """Create a new assistant."""
        ...
    
    def get_assistant(self, assistant_id: str) -> Dict[str, Any]:
        """Get assistant details."""
        ...
    
    def delete_assistant(self, assistant_id: str) -> bool:
        """Delete an assistant."""
        ...
    
    def list_assistants(self) -> List[Dict[str, Any]]:
        """List all assistants."""
        ...
