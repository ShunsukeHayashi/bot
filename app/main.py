import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.line_bot.line_bot import get_line_bot
from app.database.supabase_client import get_supabase_client
from app.agent.agent_manager import get_agent_manager

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

line_bot = get_line_bot()

agent_manager = get_agent_manager()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/webhook")
async def webhook(request: Request):
    """
    Handle LINE webhook events.
    """
    signature = request.headers.get("X-Line-Signature", "")
    
    body = await request.body()
    body_text = body.decode("utf-8")
    
    logger.info(f"Received webhook request with signature: {signature}")
    logger.info(f"Webhook body: {body_text}")
    
    try:
        if line_bot.handle_webhook(signature, body_text):
            return JSONResponse(content={"status": "ok"})
        else:
            logger.warning("Webhook validation failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error handling webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
