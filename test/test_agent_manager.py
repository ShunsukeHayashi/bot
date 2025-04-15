import pytest
from unittest.mock import MagicMock, patch

from app.agent.agent_manager import AgentManager

@pytest.fixture
def agent_manager():
    manager = AgentManager()
    manager.intent_analyzer = MagicMock()
    manager.devin_api = MagicMock()
    return manager

def test_process_message(agent_manager):
    agent_manager.intent_analyzer.analyze.return_value = {
        "type": "question",
        "requires_devin_api": False,
        "raw_message": "What is the weather?"
    }
    
    agent_manager._generate_response = MagicMock(return_value="It's sunny today!")
    
    result = agent_manager.process_message(
        "What is the weather?",
        "test_user",
        {"user_id": "test_user", "context": []}
    )
    
    assert "message" in result
    assert result["message"] == "It's sunny today!"
    assert "conversation_state" in result
