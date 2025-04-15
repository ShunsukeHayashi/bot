import os
import logging
from typing import Dict, Any, List, Optional, Protocol
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhooks.models import MessageEvent, Event
from linebot.v3.webhooks.models.text_message_content import TextMessageContent
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.v3.messaging.models import (
    TextMessage, ReplyMessageRequest
)

from app.agent.agent_manager import get_agent_manager, AgentManager
from app.database.supabase_client import get_supabase_client, SupabaseClient

logger = logging.getLogger(__name__)

class MessageHandler(Protocol):
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

class LineBot:
    """
    LINE bot implementation using LINE Messaging API SDK V3.
    
    This class handles webhook events from LINE and processes messages
    using the provided message handler and database client.
    """
    
    def __init__(
        self, 
        channel_secret: Optional[str] = None, 
        channel_access_token: Optional[str] = None,
        message_handler: Optional[MessageHandler] = None,
        database_client: Optional[DatabaseClient] = None
    ):
        """
        Initialize the LINE bot.
        
        Args:
            channel_secret: LINE channel secret
            channel_access_token: LINE channel access token
            message_handler: Component for processing messages
            database_client: Component for database operations
        """
        self.channel_secret = channel_secret or os.getenv("LINE_CHANNEL_SECRET")
        self.channel_access_token = channel_access_token or os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        
        # Initialize LINE API client and webhook handler
        self._initialize_line_client()
        
        # Initialize message handler and database client
        self.message_handler = message_handler or get_agent_manager()
        self.database_client = database_client or get_supabase_client()
    
    def _initialize_line_client(self) -> None:
        """Initialize LINE API client and webhook handler."""
        if not self.channel_secret or not self.channel_access_token:
            logger.warning("LINE channel secret or access token not set. LINE bot will not work properly.")
            self.line_bot_api = None
            self.handler = None
        else:
            configuration = Configuration(access_token=self.channel_access_token)
            self.line_bot_api = MessagingApi(ApiClient(configuration))
            self.handler = WebhookHandler(self.channel_secret)
            
            self._setup_handlers()
            
            logger.info("LINE bot initialized")
    
    def _setup_handlers(self) -> None:
        """Set up the handlers for LINE events."""
        if not self.handler:
            logger.warning("LINE handler not initialized. Skipping handler registration.")
            return
            
        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_message(event: Event) -> None:
            """Handle message events."""
            logger.info(f"Handling message event: {event}")
            self._handle_text_message(event)
        
        @self.handler.default()
        def default(event: Event) -> None:
            """Handle default events."""
            logger.info(f"Received default event: {event}")
        
        logger.info("LINE bot handlers registered")
    
    def handle_webhook(self, signature: str, body: str) -> bool:
        """
        Handle webhook events from LINE.
        
        Args:
            signature: X-Line-Signature header value
            body: Request body string
            
        Returns:
            bool: True if the webhook was handled successfully, False otherwise
        """
        if not self.handler:
            logger.warning("LINE handler not initialized. Skipping webhook handling.")
            return False
        
        logger.debug(f"Handling webhook with signature: {signature}")
        logger.debug(f"Webhook body: {body}")
        
        try:
            self.handler.handle(body, signature)
            logger.info("Webhook handled successfully")
            return True
        except InvalidSignatureError:
            logger.error("Invalid signature")
            return False
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False
    
    def _handle_text_message(self, event: MessageEvent) -> None:
        """
        Handle text message events from LINE.
        
        Args:
            event: MessageEvent containing a TextMessageContent
        """
        if not self.line_bot_api:
            logger.warning("LINE bot API not initialized. Skipping message handling.")
            return
        
        try:
            message_text = event.message.text
            user_id = self._get_user_id_from_event(event)
            
            conversation_state = self.database_client.get_conversation_state(user_id)
            
            response = self.message_handler.process_message(message_text, user_id, conversation_state)
            
            self.database_client.store_conversation_state(user_id, response.get("conversation_state", {}))
            
            self._send_response(event.reply_token, response.get("message", ""))
            
            logger.info(f"Handled text message from user {user_id}")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            self._send_error_response(event.reply_token)
    
    def _get_user_id_from_event(self, event: MessageEvent) -> str:
        """
        Extract user ID from event.
        
        Args:
            event: MessageEvent
            
        Returns:
            str: User ID or "unknown" if not available
        """
        return event.source.user_id if hasattr(event.source, 'user_id') else "unknown"
    
    def _send_response(self, reply_token: str, message: str) -> None:
        """
        Send response to user.
        
        Args:
            reply_token: LINE reply token
            message: Message to send
        """
        try:
            self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=message or "Sorry, I couldn't process your request.")]
                )
            )
        except Exception as e:
            logger.error(f"Error sending response: {e}")
    
    def _send_error_response(self, reply_token: str) -> None:
        """
        Send error response to user.
        
        Args:
            reply_token: LINE reply token
        """
        try:
            self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text="Sorry, an error occurred.")]
                )
            )
        except Exception as e:
            logger.error(f"Error sending error response: {e}")

def get_line_bot() -> LineBot:
    """
    Get a LINE bot instance.
    
    Returns:
        LineBot: A LINE bot instance
    """
    return LineBot()
