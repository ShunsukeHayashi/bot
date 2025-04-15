import os
import logging
import json
from typing import Dict, Any, Optional
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

from app.agent.agent_manager import get_agent_manager
from app.database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class TelegramBot:
    """
    Telegram bot for handling messages and interactions.
    
    This class provides a client for interacting with the Telegram Bot API,
    handling incoming messages, and sending responses.
    """
    
    def __init__(
        self, 
        token: Optional[str] = None, 
        webhook_url: Optional[str] = None
    ):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Telegram bot token
            webhook_url: Webhook URL for receiving updates
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_url = webhook_url or os.getenv("TELEGRAM_WEBHOOK_URL")
        
        if not self.token:
            logger.warning("Telegram bot token not set. Bot will not function properly.")
            self.application = None
        else:
            try:
                self.application = Application.builder().token(self.token).build()
                
                self.application.add_handler(CommandHandler("start", self.start_command))
                self.application.add_handler(CommandHandler("help", self.help_command))
                self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
                
                logger.info("Telegram bot initialized")
            except Exception as e:
                logger.error(f"Error initializing Telegram bot: {e}")
                self.application = None
        
        self.agent_manager = get_agent_manager()
        self.database_client = get_supabase_client()
    
    async def start_command(self, update: Update, context: CallbackContext) -> None:
        """
        Handle the /start command.
        
        Args:
            update: Update from Telegram
            context: Callback context
        """
        user_id = str(update.effective_user.id)
        
        welcome_message = (
            "こんにちは！AIアシスタントボットへようこそ。\n\n"
            "質問や依頼があれば、お気軽にメッセージをお送りください。"
            "OpenAI Assistantを活用して、様々な質問に答えたり、タスクをサポートしたりします。\n\n"
            "コマンド一覧:\n"
            "/help - ヘルプメッセージを表示します"
        )
        
        await update.message.reply_text(welcome_message)
        
        logger.info(f"Sent welcome message to user {user_id}")
    
    async def help_command(self, update: Update, context: CallbackContext) -> None:
        """
        Handle the /help command.
        
        Args:
            update: Update from Telegram
            context: Callback context
        """
        user_id = str(update.effective_user.id)
        
        help_message = (
            "AIアシスタントボットのヘルプ:\n\n"
            "このボットは、OpenAI Assistantを活用して質問に答えたり、タスクをサポートしたりします。\n\n"
            "使い方:\n"
            "- 質問や依頼を自然な日本語で送信してください\n"
            "- 複雑な質問や技術的な内容にも対応します\n\n"
            "コマンド一覧:\n"
            "/start - ウェルカムメッセージを表示します\n"
            "/help - このヘルプメッセージを表示します"
        )
        
        await update.message.reply_text(help_message)
        
        logger.info(f"Sent help message to user {user_id}")
    
    async def handle_message(self, update: Update, context: CallbackContext) -> None:
        """
        Handle text messages.
        
        Args:
            update: Update from Telegram
            context: Callback context
        """
        try:
            user_id = str(update.effective_user.id)
            message_text = update.message.text
            
            logger.info(f"Received message from user {user_id}: {message_text}")
            
            conversation_state = self.database_client.get_conversation_state(user_id) or {}
            
            response = self.agent_manager.process_message(message_text, user_id, conversation_state)
            
            self.database_client.store_conversation_state(user_id, response.get("conversation_state", {}))
            
            try:
                await update.message.reply_text(response.get("message", ""))
            except Exception as reply_error:
                logger.warning(f"Could not reply to message: {reply_error}")
            
            logger.info(f"Handled text message from user {user_id}")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            try:
                await update.message.reply_text("申し訳ありません、エラーが発生しました。")
            except Exception:
                logger.warning("Could not send error message")
    
    async def setup_webhook(self) -> bool:
        """
        Set up webhook for receiving updates.
        
        Returns:
            bool: True if webhook was set up successfully, False otherwise
        """
        if not self.token or not self.webhook_url or not self.application:
            logger.warning("Cannot set up webhook: token, webhook URL, or application not set")
            return False
        
        try:
            await self.application.initialize()
            
            webhook_path = f"/webhook/{self.token}"
            webhook_url = f"{self.webhook_url.rstrip('/')}{webhook_path}"
            
            await self.application.bot.set_webhook(url=webhook_url)
            
            logger.info(f"Webhook set up at {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            return False
    
    async def handle_webhook(self, update_json: bytes) -> bool:
        """
        Handle webhook update.
        
        Args:
            update_json: JSON data from webhook
            
        Returns:
            bool: True if update was handled successfully, False otherwise
        """
        if not self.application:
            logger.warning("Cannot handle webhook: application not set")
            return False
        
        try:
            update = Update.de_json(json.loads(update_json), self.application.bot)
            
            if not update:
                logger.warning("Invalid update received")
                return False
            
            await self.application.process_update(update)
            
            logger.info("Webhook update processed successfully")
            return True
        except Exception as e:
            logger.error(f"Error handling webhook update: {e}")
            return False

def get_telegram_bot() -> TelegramBot:
    """
    Get a Telegram bot instance.
    
    Returns:
        TelegramBot: A Telegram bot instance
    """
    return TelegramBot()
