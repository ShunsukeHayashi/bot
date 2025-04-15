import os
import logging
import json
from typing import Dict, Any, List, Optional, Set
import re

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    """
    Intent analyzer for determining user intent from messages.
    
    This class analyzes user messages to determine the intent type,
    whether the message requires a tool call, and extracts parameters
    for tool calls if needed.
    """
    
    def __init__(
        self,
        question_patterns: Optional[List[str]] = None,
        request_patterns: Optional[List[str]] = None,
        greeting_patterns: Optional[List[str]] = None,
        farewell_patterns: Optional[List[str]] = None,
        devin_keywords: Optional[List[str]] = None
    ):
        """
        Initialize the intent analyzer.
        
        Args:
            question_patterns: Regex patterns for identifying question intents
            request_patterns: Regex patterns for identifying request intents
            greeting_patterns: Regex patterns for identifying greeting intents
            farewell_patterns: Regex patterns for identifying farewell intents
            devin_keywords: Keywords that indicate a need for Devin API
        """
        # Initialize intent patterns with defaults if not provided
        self.question_patterns = question_patterns or [
            r'^what\s.+\?$',
            r'^how\s.+\?$',
            r'^why\s.+\?$',
            r'^when\s.+\?$',
            r'^where\s.+\?$',
            r'^who\s.+\?$',
            r'^can\s.+\?$',
            r'.+\?$'
        ]
        
        self.request_patterns = request_patterns or [
            r'^please\s.+',
            r'^could you\s.+',
            r'^can you\s.+',
            r'^would you\s.+',
            r'^I need\s.+',
            r'^I want\s.+'
        ]
        
        self.greeting_patterns = greeting_patterns or [
            r'^hi$',
            r'^hello$',
            r'^hey$',
            r'^good morning$',
            r'^good afternoon$',
            r'^good evening$'
        ]
        
        self.farewell_patterns = farewell_patterns or [
            r'^bye$',
            r'^goodbye$',
            r'^see you$',
            r'^talk to you later$',
            r'^farewell$'
        ]
        
        self.devin_keywords = devin_keywords or [
            "code", "programming", "develop", "build", "create", "generate",
            "analyze", "debug", "fix", "implement", "deploy", "automate"
        ]
        
        self._compile_patterns()
        
        logger.info("Intent analyzer initialized")
    
    def _compile_patterns(self) -> None:
        """
        Compile regex patterns for better performance.
        """
        self.compiled_question_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.question_patterns]
        self.compiled_request_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.request_patterns]
        self.compiled_greeting_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.greeting_patterns]
        self.compiled_farewell_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.farewell_patterns]
        
        self.devin_keywords_set = set(self.devin_keywords)
    
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
            
            # Determine intent type
            intent_type = self._determine_intent_type(message_lower)
            
            # Determine if Devin API is required
            requires_devin_api = self._requires_devin_api(message_lower)
            
            # Extract parameters if needed
            parameters = self._extract_parameters(message) if requires_devin_api else {}
            
            # Determine tool name if Devin API is required
            tool_name = self._determine_tool_name(message_lower) if requires_devin_api else None
            
            intent = {
                "type": intent_type,
                "requires_devin_api": requires_devin_api,
                "tool_name": tool_name,
                "parameters": parameters,
                "raw_message": message
            }
            
            logger.debug(f"Analyzed intent: {intent}")
            return intent
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
        for pattern in self.compiled_question_patterns:
            if pattern.search(message):
                return "question"
        
        for pattern in self.compiled_request_patterns:
            if pattern.search(message):
                return "request"
        
        for pattern in self.compiled_greeting_patterns:
            if pattern.search(message):
                return "greeting"
        
        for pattern in self.compiled_farewell_patterns:
            if pattern.search(message):
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
        for keyword in self.devin_keywords:
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
        # Determine the appropriate tool based on message content
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

def get_intent_analyzer() -> IntentAnalyzer:
    """
    Get an intent analyzer instance.
    
    Returns:
        IntentAnalyzer: An intent analyzer instance
    """
    return IntentAnalyzer()
