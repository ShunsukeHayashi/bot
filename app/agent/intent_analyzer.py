import os
import logging
import json
from typing import Dict, Any, List, Optional
import re

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntentAnalyzer:
    def __init__(self):
        """
        Initialize the intent analyzer.
        """
        self.question_patterns = [
            r'^what\s.+\?$',
            r'^how\s.+\?$',
            r'^why\s.+\?$',
            r'^when\s.+\?$',
            r'^where\s.+\?$',
            r'^who\s.+\?$',
            r'^can\s.+\?$',
            r'.+\?$'
        ]
        
        self.request_patterns = [
            r'^please\s.+',
            r'^could you\s.+',
            r'^can you\s.+',
            r'^would you\s.+',
            r'^I need\s.+',
            r'^I want\s.+'
        ]
        
        self.greeting_patterns = [
            r'^hi$',
            r'^hello$',
            r'^hey$',
            r'^good morning$',
            r'^good afternoon$',
            r'^good evening$'
        ]
        
        self.farewell_patterns = [
            r'^bye$',
            r'^goodbye$',
            r'^see you$',
            r'^talk to you later$',
            r'^farewell$'
        ]
        
        logger.info("Intent analyzer initialized")
    
    def analyze(self, message: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze a message to determine the user's intent.
        
        Args:
            message: User message
            context: Conversation context
            
        Returns:
            Dict[str, Any]: Analyzed intent
        """
        try:
            message_lower = message.lower()
            
            intent_type = self._determine_intent_type(message_lower)
            
            requires_devin_api = self._requires_devin_api(message_lower)
            
            parameters = self._extract_parameters(message) if requires_devin_api else {}
            
            tool_name = self._determine_tool_name(message_lower) if requires_devin_api else None
            
            return {
                "type": intent_type,
                "requires_devin_api": requires_devin_api,
                "tool_name": tool_name,
                "parameters": parameters,
                "raw_message": message
            }
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            return {"type": "general", "requires_devin_api": False, "raw_message": message}
    
    def _determine_intent_type(self, message: str) -> str:
        """
        Determine the type of intent from the message.
        
        Args:
            message: User message in lowercase
            
        Returns:
            str: Intent type
        """
        for pattern in self.question_patterns:
            if re.search(pattern, message):
                return "question"
        
        for pattern in self.request_patterns:
            if re.search(pattern, message):
                return "request"
        
        for pattern in self.greeting_patterns:
            if re.search(pattern, message):
                return "greeting"
        
        for pattern in self.farewell_patterns:
            if re.search(pattern, message):
                return "farewell"
        
        return "general"
    
    def _requires_devin_api(self, message: str) -> bool:
        """
        Determine if the message requires Devin API.
        
        Args:
            message: User message in lowercase
            
        Returns:
            bool: True if Devin API is required, False otherwise
        """
        devin_keywords = [
            "code", "programming", "develop", "build", "create", "generate",
            "analyze", "debug", "fix", "implement", "deploy", "automate"
        ]
        
        for keyword in devin_keywords:
            if keyword in message:
                return True
        
        return False
    
    def _determine_tool_name(self, message: str) -> str:
        """
        Determine the tool name based on the message.
        
        Args:
            message: User message in lowercase
            
        Returns:
            str: Tool name
        """
        if "code" in message or "programming" in message:
            return "code_assistant"
        elif "analyze" in message:
            return "code_analyzer"
        elif "debug" in message or "fix" in message:
            return "code_debugger"
        else:
            return "general_assistant"
    
    def _extract_parameters(self, message: str) -> Dict[str, Any]:
        """
        Extract parameters from the message.
        
        Args:
            message: User message
            
        Returns:
            Dict[str, Any]: Extracted parameters
        """
        return {"query": message}
