import os
import pytest
from unittest.mock import MagicMock, patch
from linebot.v3.webhooks.models import MessageEvent, Source, UserSource
from linebot.v3.webhooks.models.text_message_content import TextMessageContent

from app.line_bot.line_bot import LineBot

@pytest.fixture
def line_bot():
    with patch.dict(os.environ, {
        "LINE_CHANNEL_SECRET": "test_secret",
        "LINE_CHANNEL_ACCESS_TOKEN": "test_token"
    }):
        return LineBot()

@pytest.fixture
def message_event():
    source = UserSource(user_id="test_user")
    return MessageEvent(
        reply_token="test_reply_token",
        source=source,
        timestamp=1234567890,
        message=TextMessageContent(
            id="test_message_id",
            text="Hello, bot!"
        )
    )

def test_handle_webhook(line_bot):
    line_bot.handler = MagicMock()
    line_bot.handler.handle.return_value = None
    
    result = line_bot.handle_webhook("valid_signature", "{}")
    assert result is True
    line_bot.handler.handle.assert_called_once_with("{}", "valid_signature")
    
    line_bot.handler.handle.side_effect = Exception("Invalid signature")
    result = line_bot.handle_webhook("invalid_signature", "{}")
    assert result is False
