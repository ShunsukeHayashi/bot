import os
import logging
import json
from typing import Dict, Any, Optional
import requests

from app.protocols.message_protocols import GASExecutorProtocol

logger = logging.getLogger(__name__)

class GASClient(GASExecutorProtocol):
    """
    GAS client for executing scripts in Google Apps Script environment.
    
    This class provides a client for interacting with the GAS interpreter,
    allowing for execution of JavaScript code with parameters and context.
    """
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize the GAS client.
        
        Args:
            api_key: GAS API key for authentication
            api_url: GAS API URL
        """
        self.api_key = api_key or os.getenv("GAS_API_KEY")
        self.api_url = api_url or os.getenv("GAS_API_URL")
        
        if not self.api_key:
            logger.warning("GAS API key not set. API calls will not work.")
        
        if not self.api_url:
            logger.warning("GAS API URL not set. API calls will not work.")
        
        logger.info("GAS client initialized")
    
    def execute_script(self, script: str, title: str) -> Dict[str, Any]:
        """
        Execute a script in GAS environment.
        
        Args:
            script: JavaScript code to execute
            title: Title for the execution
            
        Returns:
            Dict[str, Any]: Execution result
        """
        if not self.api_key or not self.api_url:
            logger.warning("GAS API key or URL not set. Returning error response.")
            return self._create_error_response("GAS API設定が不完全です。APIキーとURLを確認してください。")
        
        try:
            payload = {
                "script": script,
                "title": title,
                "apiKey": self.api_key
            }
            
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload
            )
            
            return self._process_response(response)
        except Exception as e:
            logger.error(f"Error calling GAS API: {e}")
            return self._create_error_response(f"GAS APIの呼び出し中にエラーが発生しました: {e}")
    
    def _process_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Process the API response.
        
        Args:
            response: API response
            
        Returns:
            Dict[str, Any]: Processed response
        """
        try:
            data = response.json()
            
            if response.status_code == 200 and data.get("success"):
                return {
                    "success": True,
                    "result": data.get("result", "結果がありません")
                }
            else:
                error_message = data.get("error", f"HTTP {response.status_code}: {response.text}")
                logger.error(f"Error executing script: {error_message}")
                return self._create_error_response(error_message)
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return self._create_error_response(f"レスポンスの処理中にエラーが発生しました: {e}")
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """
        Create an error response.
        
        Args:
            message: Error message
            
        Returns:
            Dict[str, Any]: Error response
        """
        return {
            "success": False,
            "error": message
        }

def get_gas_client() -> GASClient:
    """
    Get a GAS client instance.
    
    Returns:
        GASClient: A GAS client instance
    """
    return GASClient()
