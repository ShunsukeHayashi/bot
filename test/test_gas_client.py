import os
import pytest
from unittest.mock import MagicMock, patch
import json
import requests

from app.gas_integration.gas_client import GASClient

@pytest.fixture
def gas_client():
    with patch.dict(os.environ, {
        "GAS_API_KEY": "test_api_key",
        "GAS_API_URL": "https://test.gas.url/exec"
    }):
        return GASClient()

@pytest.mark.parametrize("success,result,error", [
    (True, "Hello, World!", None),
    (False, None, "Script execution error")
])
def test_execute_script(gas_client, success, result, error):
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    response_data = {"success": success}
    if success:
        response_data["result"] = result
    else:
        response_data["error"] = error
    
    mock_response.json.return_value = response_data
    
    with patch("requests.post", return_value=mock_response):
        response = gas_client.execute_script("console.log('test')", "Test Script")
        
        assert response["success"] == success
        if success:
            assert response["result"] == result
        else:
            assert response["error"] == error

def test_execute_script_with_exception(gas_client):
    with patch("requests.post", side_effect=Exception("Connection error")):
        response = gas_client.execute_script("console.log('test')", "Test Script")
        
        assert response["success"] is False
        assert "Connection error" in response["error"]

def test_execute_script_without_api_key(gas_client):
    gas_client.api_key = None
    
    response = gas_client.execute_script("console.log('test')", "Test Script")
    
    assert response["success"] is False
    assert "API設定" in response["error"]
