"""
TelegramとGAS（Google Apps Script）を連携させるエージェント例

このモジュールは、Telegramボットを使ってGASスクリプトを実行する例を示します。
ユーザーがTelegramボットにJavaScriptコードを送信すると、
GASインタープリターがそのコードを実行し、結果をTelegramボットが返します。
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from app.telegram_bot.telegram_bot import TelegramBot
from app.agent.agent_manager import AgentManager
from app.gas_integration.gas_client import GASClient
from app.agent.intent_analyzer import IntentAnalyzer

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    メイン関数 - GAS連携Telegramボットの実行例
    """
    gas_api_key = os.getenv("GAS_API_KEY")
    gas_api_url = os.getenv("GAS_API_URL")
    
    if not gas_api_key or not gas_api_url:
        logger.error("GAS_API_KEY または GAS_API_URL が設定されていません")
        print("環境変数を設定してください：")
        print("GAS_API_KEY: GASインタープリターのAPIキー")
        print("GAS_API_URL: GASインタープリターのエンドポイントURL")
        return
    
    intent_analyzer = IntentAnalyzer(
        devin_keywords=["code", "programming", "develop", "build", "create", "generate",
                        "analyze", "debug", "fix", "implement", "deploy", "automate",
                        "execute", "run", "gas", "script", "javascript", "js"]
    )
    
    gas_client = GASClient(api_key=gas_api_key, api_url=gas_api_url)
    
    agent_manager = AgentManager(
        intent_analyzer=intent_analyzer,
        gas_executor=gas_client
    )
    
    telegram_bot = TelegramBot(
        message_handler=agent_manager
    )
    
    if await telegram_bot.setup_webhook():
        logger.info("Telegramボットのウェブフックが正常に設定されました")
    else:
        logger.error("Telegramボットのウェブフック設定に失敗しました")
    
    print("\nGASインタープリター連携Telegramボットの使用方法:")
    print("1. Telegramボットに以下のようなメッセージを送信:")
    print("   ```javascript")
    print("   const name = 'World';")
    print("   return `Hello, ${name}!`;")
    print("   ```")
    print("2. GASインタープリターがコードを実行し、結果をボットが返します")
    print("3. 自然言語でも「GASでこのスクリプトを実行して」のように指示できます")
    
    print("\nボットは実行中です。Ctrl+Cで終了できます...\n")
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nボットを終了します...")

if __name__ == "__main__":
    asyncio.run(main())
