import os
import logging
import json
from typing import Dict, Any, List, Optional, Protocol

from app.protocols.message_protocols import IntentAnalyzerProtocol, ToolExecutorProtocol, GASExecutorProtocol
from app.agent.intent_analyzer import IntentAnalyzer, get_intent_analyzer
from app.devin_integration.devin_api import DevinAPI, get_devin_api
from app.gas_integration.gas_client import GASClient, get_gas_client

logger = logging.getLogger(__name__)

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

class AgentManager:
    """
    Agent manager for processing messages and generating responses.
    
    This class coordinates between the intent analyzer and tool executor
    to process user messages and generate appropriate responses.
    """
    
    def __init__(
        self, 
        intent_analyzer: Optional[IntentAnalyzerProtocol] = None,
        tool_executor: Optional[ToolExecutorProtocol] = None,
        gas_executor: Optional[GASExecutorProtocol] = None,
        max_context_length: int = 10
    ):
        """
        Initialize the agent manager.
        
        Args:
            intent_analyzer: Component for analyzing user intent
            tool_executor: Component for executing tools
            gas_executor: Component for executing GAS scripts
            max_context_length: Maximum number of messages to keep in context
        """
        self.intent_analyzer = intent_analyzer or get_intent_analyzer()
        self.tool_executor = tool_executor or get_devin_api()
        self.gas_executor = gas_executor or get_gas_client()
        self.max_context_length = max_context_length
        
        logger.info("Agent manager initialized")
    
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message and generate a response.
        
        Args:
            message: User message
            user_id: User identifier
            conversation_state: Current conversation state
            
        Returns:
            Dict[str, Any]: Response data including message and updated conversation state
        """
        try:
            # Update conversation context with user message
            context = self._update_context(conversation_state.get("context", []), message, "user")
            
            intent = self.intent_analyzer.analyze(message, context)
            
            response_content = self._generate_response(message, user_id, intent, context)
            
            context = self._update_context(context, response_content, "assistant")
            
            # Create updated conversation state
            updated_state = self._create_updated_state(user_id, context, intent)
            
            return {
                "message": response_content,
                "conversation_state": updated_state
            }
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "message": "Sorry, I encountered an error while processing your message.",
                "conversation_state": conversation_state
            }
    
    def _update_context(self, context: List[Dict[str, Any]], message: str, role: str) -> List[Dict[str, Any]]:
        """
        Update conversation context with a new message.
        
        Args:
            context: Current conversation context
            message: Message to add to context
            role: Role of the message sender ("user" or "assistant")
            
        Returns:
            List[Dict[str, Any]]: Updated conversation context
        """
        updated_context = context.copy()
        
        updated_context.append({"role": role, "content": message})
        
        if len(updated_context) > self.max_context_length:
            updated_context = updated_context[-self.max_context_length:]
        
        return updated_context
    
    def _create_updated_state(self, user_id: str, context: List[Dict[str, Any]], intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create updated conversation state.
        
        Args:
            user_id: User identifier
            context: Conversation context
            intent: Analyzed intent
            
        Returns:
            Dict[str, Any]: Updated conversation state
        """
        return {
            "user_id": user_id,
            "context": context,
            "intent": intent
        }
    
    def _generate_response(self, message: str, user_id: str, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Generate a response based on intent and context.
        
        Args:
            message: User message
            user_id: User identifier
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Generated response
        """
        try:
            if intent.get("requires_devin_api", False):
                if intent.get("tool_name") == "gas_executor":
                    return self._handle_gas_intent(intent, context)
                return self._handle_tool_intent(intent, context)
            
            intent_type = intent.get("type", "general")
            
            if intent_type == "question":
                return self._handle_question_intent(intent, context)
            elif intent_type == "request":
                return self._handle_request_intent(intent, context)
            elif intent_type == "greeting":
                return "Hello! How can I assist you today?"
            elif intent_type == "farewell":
                return "Goodbye! Feel free to message me anytime you need assistance."
            else:
                return "I'm here to help. What would you like to know or do?"
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I couldn't generate a proper response. Please try again."
    
    def _handle_tool_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle intent that requires a tool call.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response from the tool
        """
        try:
            response = self.tool_executor.execute_tool(
                tool_name=intent.get("tool_name", "general_assistant"),
                parameters=intent.get("parameters", {}),
                context=context
            )
            return response.get("content", "I couldn't complete the operation.")
        except Exception as e:
            logger.error(f"Error executing tool: {e}")
            return "I encountered an error while trying to use the required tools."
    
    def _handle_question_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle question intent.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response to the question
        """
        return "Based on your question, I would say..."
    
    def _handle_request_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle request intent.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response to the request
        """
        return "I'll help you with that request..."
    
    def _handle_gas_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle intent that requires GAS script execution.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response from the GAS execution
        """
        try:
            script = intent.get("raw_message", "")
            if "```" in script:
                code_blocks = script.split("```")
                if len(code_blocks) >= 3:  # At least one code block
                    script = code_blocks[1]
            
            response = self.gas_executor.execute_script(
                script=script,
                title=f"Telegram Execution {intent.get('type', 'script')}"
            )
            
            if response.get("success"):
                return f"🎉 スクリプトの実行に成功しました！\n\n結果: {response.get('result', '結果がありません')}"
            else:
                return f"⚠️ スクリプトの実行中にエラーが発生しました：\n{response.get('error', 'エラーの詳細がありません')}"
        except Exception as e:
            logger.error(f"Error executing GAS script: {e}")
            return "GASスクリプトの実行中にエラーが発生しました。もう一度お試しください。"

def get_agent_manager() -> AgentManager:
    """
    Get an agent manager instance.
    
    Returns:
        AgentManager: An agent manager instance
    """
    return AgentManager()
