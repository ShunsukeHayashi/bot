import os
import logging
import json
from typing import Dict, Any, List, Optional
import requests

logger = logging.getLogger(__name__)

class DevinAPI:
    """
    Devin API client for executing tool calls.
    
    This class provides a client for interacting with the Devin API,
    allowing for execution of tool calls with parameters and context.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize the Devin API client.
        
        Args:
            api_key: Devin API key for authentication
            api_url: Devin API URL
        """
        self.api_key = api_key or os.getenv("DEVIN_API_KEY")
        self.api_url = api_url or os.getenv("DEVIN_API_URL", "https://api.devin.com/v1")
        
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
            return self._create_error_response("I couldn't access the required tools. Please check the API configuration.")
        
        try:
            payload = self._prepare_payload(tool_name, parameters, context)
            
            response = self._execute_api_request(payload)
            
            return self._process_response(response)
        except Exception as e:
            logger.error(f"Error calling Devin API: {e}")
            return self._create_error_response("An error occurred while trying to use the tool.")
    
    def _prepare_payload(self, tool_name: str, parameters: Dict[str, Any], context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare the payload for the API request.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            context: Conversation context
            
        Returns:
            Dict[str, Any]: Prepared payload
        """
        return {
            "tool": tool_name,
            "parameters": parameters,
            "context": context
        }
    
    def _execute_api_request(self, payload: Dict[str, Any]) -> requests.Response:
        """
        Execute the API request.
        
        Args:
            payload: Request payload
            
        Returns:
            requests.Response: API response
        """
        return requests.post(
            f"{self.api_url}/tools/execute",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json=payload
        )
    
    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Process the API response.
        
        Args:
            response: API response
            
        Returns:
            Dict[str, Any]: Processed response
        """
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Error executing tool: {response.status_code} - {response.text}")
            return self._create_error_response(f"Error executing tool: {response.status_code}")
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Dict[str, Any]: Error response
        """
        return {"content": message}

def get_devin_api() -> DevinAPI:
    """
    Get a Devin API client instance.
    
    Returns:
        DevinAPI: A Devin API client instance
    """
    return DevinAPI()
