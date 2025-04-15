import os
import json
import unittest
from unittest import mock
from typing import Dict, Any

from app.openai_integration.openai_assistant import OpenAIAssistant

class TestOpenAIAssistant(unittest.TestCase):
    """Test OpenAI Assistant functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.env_patcher = mock.patch.dict(os.environ, {
            "OPENAI_API_KEY": "test-api-key",
            "OPENAI_ASSISTANT_ID": "test-assistant-id",
            "OPENAI_MODEL": "gpt-4-turbo"
        })
        self.env_patcher.start()
        
        self.openai_patcher = mock.patch("app.openai_integration.openai_assistant.OpenAI")
        self.mock_openai = self.openai_patcher.start()
        
        self.mock_client = mock.MagicMock()
        self.mock_openai.return_value = self.mock_client
        
        self.assistant = OpenAIAssistant()
    
    def tearDown(self):
        """Clean up after tests."""
        self.env_patcher.stop()
        self.openai_patcher.stop()
    
    def test_process_message(self):
        """Test processing a message."""
        mock_thread = mock.MagicMock()
        mock_thread.id = "test-thread-id"
        self.mock_client.beta.threads.create.return_value = mock_thread
        
        mock_run = mock.MagicMock()
        mock_run.status = "completed"
        mock_run.id = "test-run-id"
        self.mock_client.beta.threads.runs.create.return_value = mock_run
        self.mock_client.beta.threads.runs.retrieve.return_value = mock_run
        
        mock_content = mock.MagicMock()
        mock_content.text.value = "Test response"
        mock_message = mock.MagicMock()
        mock_message.content = [mock_content]
        mock_messages = mock.MagicMock()
        mock_messages.data = [mock_message]
        self.mock_client.beta.threads.messages.list.return_value = mock_messages
        
        response = self.assistant.process_message("Hello", "user123", {})
        
        self.assertEqual(response["message"], "Test response")
        self.assertEqual(response["conversation_state"]["openai_thread_id"], "test-thread-id")
        
        self.mock_client.beta.threads.create.assert_called_once()
        self.mock_client.beta.threads.messages.create.assert_called_once_with(
            thread_id="test-thread-id",
            role="user",
            content="Hello"
        )
        self.mock_client.beta.threads.runs.create.assert_called_once_with(
            thread_id="test-thread-id",
            assistant_id="test-assistant-id"
        )

if __name__ == "__main__":
    unittest.main()
