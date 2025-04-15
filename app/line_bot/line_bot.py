import os
import logging
from typing import Dict, Any, List, Optional
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, Configuration, ApiClient
from linebot.v3.webhooks.models import MessageEvent
from linebot.v3.webhooks.models.text_message_content import TextMessageContent
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.v3.messaging.models import (
    TextMessage, ReplyMessageRequest
)

from app.agent.agent_manager import get_agent_manager
from app.database.supabase_client import get_supabase_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LineBot:
    def __init__(self):
        """
        Initialize the LINE bot.
        """
        self.channel_secret = os.getenv("LINE_CHANNEL_SECRET")
        self.channel_access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        
        if not self.channel_secret or not self.channel_access_token:
            logger.warning("LINE channel secret or access token not set. LINE bot will not work properly.")
            self.line_bot_api = None
            self.handler = None
        else:
            configuration = Configuration(access_token=self.channel_access_token)
            self.line_bot_api = MessagingApi(ApiClient(configuration))
            self.handler = WebhookHandler(self.channel_secret)
            
            self.setup_handlers()
            
            logger.info("LINE bot initialized")
        
        self.agent_manager = get_agent_manager()
        
        self.supabase_client = get_supabase_client()
    
    def setup_handlers(self):
        """
        Set up the handlers for LINE events.
        """
        if not self.handler:
            logger.warning("LINE handler not initialized. Skipping handler registration.")
            return
            
        @self.handler.add(MessageEvent, message=TextMessageContent)
        def handle_message(event):
            logger.info(f"Handling message event: {event}")
            self.handle_text_message(event)
        
        @self.handler.default()
        def default(event):
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
        
        logger.info(f"Handling webhook with signature: {signature}")
        logger.info(f"Webhook body: {body}")
        
        try:
            self.handler.handle(body, signature)
            logger.info("Webhook handled successfully by LINE SDK handler")
            return True
        except InvalidSignatureError:
            logger.error("Invalid signature")
            return False
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return False
    
    def handle_text_message(self, event: MessageEvent) -> None:
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
            user_id = event.source.user_id if hasattr(event.source, 'user_id') else "unknown"
            
            conversation_state = self.supabase_client.get_conversation_state(user_id)
            
            response = self.agent_manager.process_message(message_text, user_id, conversation_state)
            
            self.supabase_client.store_conversation_state(user_id, response.get("conversation_state", {}))
            
            self.line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response.get("message", "Sorry, I couldn't process your request."))]
                )
            )
            
            logger.info(f"Handled text message: {message_text}")
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            
            try:
                self.line_bot_api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=[TextMessage(text="Sorry, an error occurred.")]
                    )
                )
            except Exception as reply_error:
                logger.error(f"Error sending error message: {reply_error}")

def get_line_bot() -> LineBot:
    """
    Get a LINE bot instance.
    
    Returns:
        LineBot: A LINE bot instance
    """
    line_bot = LineBot()
    return line_bot
