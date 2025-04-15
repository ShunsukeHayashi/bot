import asyncio
import os
from dotenv import load_dotenv
from app.telegram_bot.telegram_bot import get_telegram_bot

async def setup():
    load_dotenv()
    
    print(f"TELEGRAM_BOT_TOKEN: {os.getenv('TELEGRAM_BOT_TOKEN')}")
    print(f"TELEGRAM_WEBHOOK_URL: {os.getenv('TELEGRAM_WEBHOOK_URL')}")
    
    bot = get_telegram_bot()
    success = await bot.setup_webhook()
    print(f'Webhook setup: {success}')

if __name__ == "__main__":
    asyncio.run(setup())
