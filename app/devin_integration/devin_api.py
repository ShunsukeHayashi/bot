import os
import logging
import json
from typing import Dict, Any, List, Optional
import requests

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DevinAPI:
    def __init__(self):
        """
        Initialize the Devin API client.
        """
        self.api_key = os.getenv("DEVIN_API_KEY")
        self.api_url = os.getenv("DEVIN_API_URL", "https://api.devin.com/v1")
        
        if not self.api_key:
            logger.warning("Devin API key not set. API calls will not work.")
        
        logger.info("Devin API client initialized")
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute a tool call through the Devin API.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Conversation context
            
        Returns:
            Dict[str, Any]: Tool execution result
        """
        if not self.api_key:
            logger.warning("Devin API key not set. Returning mock response.")
            return {"content": "I couldn't access the required tools. Please check the API configuration."}
        
        try:
            payload = {
                "tool": tool_name,
                "parameters": parameters,
                "context": context
            }
            
            response = requests.post(
                f"{self.api_url}/tools/execute",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Error executing tool: {response.status_code} - {response.text}")
                return {"content": f"Error executing tool: {response.status_code}"}
        except Exception as e:
            logger.error(f"Error calling Devin API: {e}")
            return {"content": "An error occurred while trying to use the tool."}
