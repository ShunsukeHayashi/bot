import os
import logging
import json
from typing import Dict, Any, List, Optional, Protocol
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler as TelegramMessageHandler, filters, ContextTypes, CallbackContext
from telegram.ext.filters import MessageFilter

from app.agent.agent_manager import get_agent_manager, AgentManager
from app.database.supabase_client import get_supabase_client, SupabaseClient

logger = logging.getLogger(__name__)

class MessageHandlerProtocol(Protocol):
    """Protocol for message handling components."""
    def process_message(self, message: str, user_id: str, conversation_state: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message and return a response."""
        ...

class DatabaseClient(Protocol):
    """Protocol for database client components."""
    def get_conversation_state(self, user_id: str) -> Dict[str, Any]:
        """Get conversation state from the database."""
        ...
    
    def store_conversation_state(self, user_id: str, conversation_data: Dict[str, Any]) -> bool:
        """Store conversation state in the database."""
        ...

class TelegramBot:
    """
    Telegram bot implementation using python-telegram-bot library.
    
    This class handles webhook events from Telegram and processes messages
    using the provided message handler and database client.
    """
    
    def __init__(
        self, 
        token: Optional[str] = None,
        webhook_url: Optional[str] = None,
        message_handler: Optional[MessageHandlerProtocol] = None,
        database_client: Optional[DatabaseClient] = None
    ):
        """
        Initialize the Telegram bot.
        
        Args:
            token: Telegram bot token
            webhook_url: Webhook URL for Telegram
            message_handler: Component for processing messages
            database_client: Component for database operations
        """
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.webhook_url = webhook_url or os.getenv("TELEGRAM_WEBHOOK_URL")
        
        # Initialize Telegram application
        self._initialize_telegram_app()
        
        # Initialize message handler and database client
        self.message_handler = message_handler or get_agent_manager()
        self.database_client = database_client or get_supabase_client()
    
    def _initialize_telegram_app(self) -> None:
        """Initialize Telegram application and handlers."""
        if not self.token:
            logger.warning("Telegram bot token not set. Telegram bot will not work properly.")
            self.application = None
        else:
            self.application = Application.builder().token(self.token).build()
            
            self._setup_handlers()
            
            logger.info("Telegram bot initialized")
    
    def _setup_handlers(self) -> None:
        """Set up the handlers for Telegram events."""
        if not self.application:
            logger.warning("Telegram application not initialized. Skipping handler registration.")
            return
            
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self._handle_start))
        self.application.add_handler(CommandHandler("help", self._handle_help))
        
        # Add message handler for text messages
        self.application.add_handler(TelegramMessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        logger.info("Telegram bot handlers registered")
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text("こんにちは！何かお手伝いできることはありますか？")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command."""
        await update.message.reply_text("このボットはあなたの質問や要望に応答します。メッセージを送信してみてください。")
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages."""
        if not update.message or not update.message.text:
            return
        
        try:
            message_text = update.message.text
            user_id = str(update.effective_user.id)
            
            conversation_state = self.database_client.get_conversation_state(user_id)
            
            response = self.message_handler.process_message(message_text, user_id, conversation_state)
            
            self.database_client.store_conversation_state(user_id, response.get("conversation_state", {}))
            
            await update.message.reply_text(response.get("message", ""))
            
            logger.info(f"Handled text message from user {user_id}")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text("申し訳ありません、エラーが発生しました。")
    
    async def setup_webhook(self) -> bool:
        """
        Set up webhook for Telegram bot.
        
        Returns:
            bool: True if webhook was set up successfully, False otherwise
        """
        if not self.application or not self.webhook_url:
            logger.warning("Telegram application or webhook URL not set. Skipping webhook setup.")
            return False
        
        try:
            webhook_path = f"/webhook/{self.token}"
            webhook_url = f"{self.webhook_url.rstrip('/')}{webhook_path}"
            
            await self.application.bot.set_webhook(url=webhook_url)
            logger.info(f"Webhook set up at {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            return False
    
    async def handle_webhook(self, request_body: bytes) -> bool:
        """
        Handle webhook update from Telegram.
        
        Args:
            request_body: Request body bytes
            
        Returns:
            bool: True if the webhook was handled successfully, False otherwise
        """
        if not self.application:
            logger.warning("Telegram application not initialized. Skipping webhook handling.")
            return False
        
        try:
            update = Update.de_json(json.loads(request_body.decode("utf-8")), self.application.bot)
            await self.application.process_update(update)
            logger.info("Webhook handled successfully")
            return True
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False

def get_telegram_bot() -> TelegramBot:
    """
    Get a Telegram bot instance.
    
    Returns:
        TelegramBot: A Telegram bot instance
    """
    return TelegramBot()
