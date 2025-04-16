import logging
from typing import Dict, Any, List, Optional, Protocol

logger = logging.getLogger(__name__)

class MessageHandlerProtocol(Protocol):
    """Protocol for message handling components."""
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response."""
        ...

class DatabaseClientProtocol(Protocol):
    """Protocol for database client components."""
    def get_conversation_state(self, user_id: str) -> Dict[str, Any]:
        """Get conversation state from the database."""
        ...
    
    def store_conversation_state(self, user_id: str, conversation_data: Dict[str, Any]) -> bool:
        """Store conversation state in the database."""
        ...

class IntentAnalyzerProtocol(Protocol):
    """Protocol for intent analyzer components."""
    def analyze(self, message: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a message to determine the user's intent."""
        ...

class ToolExecutorProtocol(Protocol):
    """Protocol for tool executor components."""
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a tool call."""
        ...

class GASExecutorProtocol(Protocol):
    """Protocol for GAS executor components."""
    def execute_script(self, script: str, title: str) -> Dict[str, Any]:
        """Execute a script in GAS environment and return the result."""
        ...
