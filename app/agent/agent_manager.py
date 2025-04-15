import os
import logging
import json
from typing import Dict, Any, List, Optional

from app.agent.intent_analyzer import IntentAnalyzer
from app.devin_integration.devin_api import DevinAPI

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self):
        """
        Initialize the agent manager.
        """
        self.intent_analyzer = IntentAnalyzer()
        
        self.devin_api = DevinAPI()
        
        logger.info("Agent manager initialized")
    
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a message and generate a response.
        
        Args:
            message: User message
            user_id: LINE user ID
            conversation_state: Current conversation state
            
        Returns:
            Dict[str, Any]: Response data including message and updated conversation state
        """
        try:
            context = conversation_state.get("context", [])
            context.append({"role": "user", "content": message})
            
            if len(context) > 10:
                context = context[-10:]
            
            intent = self.intent_analyzer.analyze(message, context)
            
            response_content = self._generate_response(message, user_id, intent, context)
            
            context.append({"role": "assistant", "content": response_content})
            
            updated_state = {
                "user_id": user_id,
                "context": context,
                "intent": intent
            }
            
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
    
    def _generate_response(self, message: str, user_id: str, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Generate a response based on intent and context.
        
        Args:
            message: User message
            user_id: LINE user ID
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Generated response
        """
        try:
            if intent.get("requires_devin_api", False):
                response = self.devin_api.execute_tool(
                    tool_name=intent.get("tool_name", "general_assistant"),
                    parameters=intent.get("parameters", {}),
                    context=context
                )
                return response.get("content", "I couldn't complete the operation.")
            
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
    
    def _handle_question_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle question intent.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response to the question
        """
        return "Based on your question, I would say..." # Placeholder
    
    def _handle_request_intent(self, intent: Dict[str, Any], context: List[Dict[str, Any]]) -> str:
        """
        Handle request intent.
        
        Args:
            intent: Analyzed intent
            context: Conversation context
            
        Returns:
            str: Response to the request
        """
        return "I'll help you with that request..." # Placeholder

def get_agent_manager() -> AgentManager:
    """
    Get an agent manager instance.
    
    Returns:
        AgentManager: An agent manager instance
    """
    return AgentManager()
