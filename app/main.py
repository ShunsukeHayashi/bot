import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.telegram_bot.telegram_bot import get_telegram_bot
from app.database.supabase_client import get_supabase_client
from app.agent.agent_manager import get_agent_manager
from app.openai_integration.openai_assistant import get_openai_assistant

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

telegram_bot = get_telegram_bot()

agent_manager = get_agent_manager()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/webhook/{token}")
async def webhook(token: str, request: Request):
    """
    Handle Telegram webhook events.
    """
    # Verify token
    if token != os.getenv("TELEGRAM_BOT_TOKEN"):
        logger.warning("Invalid token")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    body = await request.body()
    
    logger.info(f"Received webhook request")
    
    try:
        if await telegram_bot.handle_webhook(body):
            return JSONResponse(content={"status": "ok"})
        else:
            logger.warning("Webhook handling failed")
            raise HTTPException(status_code=400, detail="Invalid request")
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/agent/message")
async def process_agent_message(request: Request):
    """
    Process a message through the agent.
    
    Request body:
    {
        "message": "Hello, how are you?",
        "user_id": "user123",
        "conversation_state": {}  # Optional
    }
    """
    try:
        body = await request.json()
        
        message = body.get("message")
        user_id = body.get("user_id")
        conversation_state = body.get("conversation_state", {})
        
        if not message or not user_id:
            return JSONResponse(
                status_code=400,
                content={"error": "message and user_id are required"}
            )
            
        response = agent_manager.process_message(message, user_id, conversation_state)
        
        return JSONResponse(content=response)
    except Exception as e:
        logger.error(f"Error processing agent message: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error processing message: {str(e)}"}
        )

@app.on_event("startup")
async def startup_event():
    """
    Set up webhook on startup.
    """
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_WEBHOOK_URL"):
        await telegram_bot.setup_webhook()
