import os
import pytest
from unittest.mock import MagicMock, patch
import json
from telegram import Update
from telegram.ext import Application

from app.telegram_bot.telegram_bot import TelegramBot

@pytest.fixture
def telegram_bot():
    with patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_WEBHOOK_URL": "https://test.com/webhook"
    }):
        return TelegramBot()

@pytest.fixture
def update_json():
    return {
        "update_id": 123456789,
        "message": {
            "message_id": 123,
            "from": {
                "id": 123456,
                "is_bot": False,
                "first_name": "Test",
                "username": "test_user"
            },
            "chat": {
                "id": 123456,
                "first_name": "Test",
                "username": "test_user",
                "type": "private"
            },
            "date": 1234567890,
            "text": "Hello, bot!"
        }
    }

@pytest.mark.asyncio
async def test_handle_webhook(telegram_bot, update_json):
    telegram_bot.application = MagicMock()
    telegram_bot.application.process_update = MagicMock()
    
    update_bytes = json.dumps(update_json).encode("utf-8")
    
    result = await telegram_bot.handle_webhook(update_bytes)
    assert result is True
    telegram_bot.application.process_update.assert_called_once()
    
    # Test with exception
    telegram_bot.application.process_update.side_effect = Exception("Test error")
    result = await telegram_bot.handle_webhook(update_bytes)
    assert result is False
