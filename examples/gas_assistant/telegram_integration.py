import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# GAS Assistantモジュールをインポート
try:
    from gas_assistant import EnhancedGASAgent, ExecuteGASCodeTool, AnalyzeResultTool
except ImportError as e:
    print(f"GAS Assistantモジュールのインポートに失敗しました: {e}")
    print("必要なパッケージがインストールされているか確認してください。")
    print("pip install openai-agents==0.0.10")
    raise

# ロギングの設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 環境変数からAPIキーを取得
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GAS_API_KEY = os.environ.get("GAS_API_KEY")
GAS_API_ENDPOINT = os.environ.get("GAS_API_ENDPOINT")

# チャットの状態
class ChatState:
    def __init__(self):
        self.state = "idle"
        self.useAgents = False
        self.useEnhancedAgents = False
        self.analyzeResult = False
        self.apiKey = None
        self.lastRequest = None
        self.lastResponse = None
        self.savedCodes = []
        self.savedResults = []

# チャット状態の管理
chat_states = {}

# GAS Assistantエージェントのインスタンス
agent = None

# エージェントの初期化
def initialize_agent():
    global agent
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY環境変数が設定されていません。")
    
    agent = EnhancedGASAgent(api_key=OPENAI_API_KEY)
    return agent

# チャット状態の取得
def get_chat_state(chat_id):
    if chat_id not in chat_states:
        chat_states[chat_id] = ChatState()
    return chat_states[chat_id]

# チャット状態の更新
def update_chat_state(chat_id, updates):
    chat_state = get_chat_state(chat_id)
    for key, value in updates.items():
        setattr(chat_state, key, value)
    return chat_state

# スタートコマンドのハンドラ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ボットを開始するコマンド"""
    chat_id = update.effective_chat.id
    
    # チャット状態の初期化
    update_chat_state(chat_id, {
        "state": "idle",
        "useAgents": False,
        "useEnhancedAgents": False,
        "analyzeResult": False,
        "apiKey": None,
        "lastRequest": None,
        "lastResponse": None
    })
    
    # ウェルカムメッセージの送信
    welcome_message = """🤖 *GAS Assistant へようこそ!*

Google Apps Script専門AIアシスタントです。自然言語でリクエストを入力するだけで、GASコードを生成し、実行することができます。

*使い方:*
1. GASで実現したいことを日本語で説明してください
2. AIがタスクを分析し、GASコードを生成します
3. 必要に応じて、生成されたコードを実行できます

*GASコードの特徴:*
- 関数宣言（function）を使わず、直接コードを記述
- 必ず結果をreturn文で返す形式
- 例: `const data = SpreadsheetApp.getActiveSheet().getDataRange().getValues(); return data;`

*コマンド:*
/help - ヘルプを表示
/cancel - 現在の操作をキャンセル
/settings - 設定を表示
/useagents - OpenAI Agents SDKの使用を切り替え
/useenhancedagents - 拡張Agents SDKの使用を切り替え
/analyzeresult - 実行結果の分析を切り替え

それでは、GASで実現したいことを教えてください！"""
    
    await update.message.reply_text(welcome_message, parse_mode="Markdown")

# ヘルプコマンドのハンドラ
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ヘルプを表示するコマンド"""
    help_message = """*GAS Assistant ヘルプ*

*基本的な使い方:*
1. GASで実現したいことを日本語で説明してください
2. AIがタスクを分析し、GASコードを生成します
3. 生成されたコードを実行する場合は、「実行」ボタンをクリックしてください

*コマンド一覧:*
/start - ボットを開始
/help - このヘルプを表示
/cancel - 現在の操作をキャンセル
/settings - 設定を表示
/useagents - OpenAI Agents SDKの使用を切り替え
/useenhancedagents - 拡張Agents SDKの使用を切り替え
/analyzeresult - 実行結果の分析を切り替え

*GASコードの特徴:*
- 関数宣言（function）を使わず、直接コードを記述
- 必ず結果をreturn文で返す形式
- 例: `const data = SpreadsheetApp.getActiveSheet().getDataRange().getValues(); return data;`

*APIキーの設定:*
GASコードを実行するには、Google Apps Script APIのAPIキーが必要です。
「APIキーを設定」ボタンをクリックして設定してください。

*OpenAI Agents SDKについて:*
複雑なタスクには、OpenAI Agents SDKを使用することをお勧めします。
/useagents コマンドで切り替えることができます。

*拡張Agents SDKについて:*
より高度なタスクには、拡張Agents SDKを使用することをお勧めします。
/useenhancedagents コマンドで切り替えることができます。

*実行結果分析について:*
コード実行後に結果を自動的に分析するには、実行結果分析を有効にしてください。
/analyzeresult コマンドで切り替えることができます。"""
    
    await update.message.reply_text(help_message, parse_mode="Markdown")

# キャンセルコマンドのハンドラ
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """現在の操作をキャンセルするコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if chat_state.state == "idle":
        await update.message.reply_text("現在処理中の操作はありません。")
        return
    
    # 状態をリセット
    update_chat_state(chat_id, {"state": "idle"})
    
    await update.message.reply_text("操作をキャンセルしました。")

# 設定コマンドのハンドラ
async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """設定を表示するコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # 現在の設定を取得
    agents_status = "有効" if chat_state.useAgents else "無効"
    enhanced_agents_status = "有効" if chat_state.useEnhancedAgents else "無効"
    analyze_result_status = "有効" if chat_state.analyzeResult else "無効"
    api_key_status = "設定済み" if chat_state.apiKey else "未設定"
    
    # 設定メッセージの作成
    settings_message = f"""*現在の設定*

*OpenAI Agents SDK:* {agents_status}
*拡張Agents SDK:* {enhanced_agents_status}
*実行結果分析:* {analyze_result_status}
*GAS APIキー:* {api_key_status}

設定を変更するには、以下のボタンを使用してください:"""
    
    # インラインキーボードの作成
    keyboard = [
        [InlineKeyboardButton("APIキーを設定", callback_data="set_api_key")],
        [InlineKeyboardButton(f"OpenAI Agents SDKを{'無効' if chat_state.useAgents else '有効'}にする", callback_data="toggle_agents")],
        [InlineKeyboardButton(f"拡張Agents SDKを{'無効' if chat_state.useEnhancedAgents else '有効'}にする", callback_data="toggle_enhanced_agents")],
        [InlineKeyboardButton(f"実行結果分析を{'無効' if chat_state.analyzeResult else '有効'}にする", callback_data="toggle_analyze_result")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_message, reply_markup=reply_markup, parse_mode="Markdown")

# OpenAI Agents SDKの使用を切り替えるコマンド
async def toggle_agents_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """OpenAI Agents SDKの使用を切り替えるコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    current_status = chat_state.useAgents
    
    # 現在無効で、有効にしようとしている場合
    if not current_status:
        # エラーメッセージを表示して、無効のままにする
        await update.message.reply_text(
            'OpenAI Agents SDKを有効にできません。Python環境が正しく設定されていないか、必要なライブラリがインストールされていません。\n\n' +
            '通常のコード生成機能は引き続き使用できます。'
        )
        return
    
    # 現在有効で、無効にする場合
    update_chat_state(chat_id, {"useAgents": False})
    await update.message.reply_text('OpenAI Agents SDKを無効にしました。')

# 拡張Agents SDKの使用を切り替えるコマンド
async def toggle_enhanced_agents_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """拡張Agents SDKの使用を切り替えるコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    current_status = chat_state.useEnhancedAgents
    
    # 現在無効で、有効にしようとしている場合
    if not current_status:
        # エラーメッセージを表示して、無効のままにする
        await update.message.reply_text(
            '拡張OpenAI Agents SDKを有効にできません。Python環境が正しく設定されていないか、必要なライブラリがインストールされていません。\n\n' +
            '通常のコード生成機能は引き続き使用できます。'
        )
        return
    
    # 現在有効で、無効にする場合
    update_chat_state(chat_id, {"useEnhancedAgents": False})
    await update.message.reply_text('拡張OpenAI Agents SDKを無効にしました。')

# 実行結果分析の使用を切り替えるコマンド
async def toggle_analyze_result_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """実行結果分析の使用を切り替えるコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    current_status = chat_state.analyzeResult
    
    # 現在の状態を反転
    new_status = not current_status
    update_chat_state(chat_id, {"analyzeResult": new_status})
    
    if new_status:
        await update.message.reply_text('実行結果の分析を有効にしました。コード実行後に結果が自動的に分析されます。')
    else:
        await update.message.reply_text('実行結果の分析を無効にしました。')

# コールバッククエリのハンドラ
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """コールバッククエリを処理する"""
    query = update.callback_query
    await query.answer()
    
    chat_id = query.message.chat_id
    chat_state = get_chat_state(chat_id)
    data = query.data
    
    if data == "set_api_key":
        # APIキー設定モードに移行
        update_chat_state(chat_id, {"state": "waiting_for_api_key"})
        await query.message.reply_text('Google Apps Script APIのAPIキーを入力してください:')
    
    elif data == "toggle_agents":
        # OpenAI Agents SDKの使用を切り替え
        await toggle_agents_mode(update, context)
    
    elif data == "toggle_enhanced_agents":
        # 拡張Agents SDKの使用を切り替え
        await toggle_enhanced_agents_mode(update, context)
    
    elif data == "toggle_analyze_result":
        # 実行結果分析の使用を切り替え
        await toggle_analyze_result_mode(update, context)
    
    elif data == "execute_code":
        # コードを実行
        if chat_state.lastResponse and chat_state.lastResponse.get("gasCode"):
            await execute_code(chat_id, chat_state.lastResponse["gasCode"], chat_state)
        else:
            await query.message.reply_text('実行するコードがありません。')
    
    elif data == "copy_code":
        # コードがコピーされたことを通知
        await query.message.reply_text('✅ コードをクリップボードにコピーしました。')
    
    elif data == "edit_code":
        # コード編集モードに移行
        update_chat_state(chat_id, {"state": "waiting_for_code_edit"})
        await query.message.reply_text('📝 編集したいコードを入力してください。現在のコードを送信します：')
        await query.message.reply_text(chat_state.lastResponse.get("gasCode", ""))
    
    elif data == "save_code":
        # コードを保存
        if chat_state.lastResponse and chat_state.lastResponse.get("gasCode"):
            if not hasattr(chat_state, "savedCodes"):
                chat_state.savedCodes = []
            
            chat_state.savedCodes.append({
                "title": chat_state.lastRequest.get("title", "Untitled") if chat_state.lastRequest else "Untitled",
                "code": chat_state.lastResponse["gasCode"],
                "timestamp": str(datetime.datetime.now())
            })
            
            await query.message.reply_text('✅ コードを保存しました。`/history` コマンドで保存したコードを表示できます。')
        else:
            await query.message.reply_text('保存するコードがありません。')

# メッセージハンドラ
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ユーザーメッセージを処理する"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # 状態に応じた処理
    if chat_state.state == "waiting_for_api_key":
        # APIキー入力待ち
        update_chat_state(chat_id, {
            "apiKey": update.message.text,
            "state": "idle"
        })
        await update.message.reply_text('✅ APIキーを設定しました。これでコードを実行できるようになりました。')
    
    elif chat_state.state == "waiting_for_code_edit":
        # コード編集待ち
        if chat_state.lastResponse:
            # 編集されたコードを保存
            updated_response = chat_state.lastResponse.copy()
            updated_response["gasCode"] = update.message.text
            
            update_chat_state(chat_id, {
                "lastResponse": updated_response,
                "state": "idle"
            })
            
            # 編集完了メッセージと実行ボタンを表示
            keyboard = [
                [InlineKeyboardButton("▶️ 編集したコードを実行", callback_data="execute_code")],
                [
                    InlineKeyboardButton("💾 保存", callback_data="save_code"),
                    InlineKeyboardButton("📤 共有", callback_data="share_code")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('✅ コードを編集しました。', reply_markup=reply_markup)
        else:
            update_chat_state(chat_id, {"state": "idle"})
            await update.message.reply_text('❌ コードの編集に失敗しました。新しいリクエストを送信してください。')
    
    else:
        # 通常のリクエスト処理
        await process_request(chat_id, update.message.text, update)

# リクエスト処理
async def process_request(chat_id, content, update):
    """リクエストを処理する"""
    global agent
    
    # エージェントの初期化
    if not agent:
        try:
            agent = initialize_agent()
        except Exception as e:
            await update.message.reply_text(f"エージェントの初期化に失敗しました: {str(e)}")
            return
    
    # 処理中メッセージを送信
    processing_msg = await update.message.reply_text('🔄 リクエストを処理中...')
    
    # タイトルを生成（内容の最初の10単語程度）
    title = " ".join(content.split()[:10])
    
    # リクエストを保存
    chat_state = get_chat_state(chat_id)
    chat_state.lastRequest = {
        "title": title,
        "content": content
    }
    
    # 処理ステップと進捗表示のためのアニメーション
    processing_steps = [
        {"emoji": "🔍", "text": "タスクを分析中"},
        {"emoji": "🧠", "text": "コンテキストを理解中"},
        {"emoji": "📝", "text": "プランを作成中"},
        {"emoji": "💻", "text": "GASコードを生成中"}
    ]
    
    # 処理中アニメーションの開始
    current_step = 0
    
    try:
        # 最終ステップの表示
        await processing_msg.edit_text('💻 GASコードを生成中...')
        
        # エージェントの実行
        result = await agent.run(content, analyze_result=chat_state.analyzeResult)
        
        # レスポンスからコードと説明を抽出
        response_text = result["response"]
        
        # コードセクションの抽出
        code_section = ""
        if "◤◢◤◢ GASコード生成 ◤◢◤◢" in response_text:
            code_parts = response_text.split("◤◢◤◢ GASコード生成 ◤◢◤◢")[1].split("◤◢◤◢")[0].strip()
            code_section = code_parts
            
            # コードブロックの抽出
            if "```javascript" in code_section:
                code_section = code_section.split("```javascript")[1].split("```")[0].strip()
            elif "```" in code_section:
                code_section = code_section.split("```")[1].split("```")[0].strip()
        
        # 説明セクションの抽出
        explanation_section = ""
        if "◤◢◤◢ 説明と次のステップ ◤◢◤◢" in response_text:
            explanation_section = response_text.split("◤◢◤◢ 説明と次のステップ ◤◢◤◢")[1].strip()
        
        # タスク分析セクションの抽出
        task_analysis = ""
        if "◤◢◤◢ タスク分析 ◤◢◤◢" in response_text:
            task_analysis = response_text.split("◤◢◤◢ タスク分析 ◤◢◤◢")[1].split("◤◢◤◢")[0].strip()
        
        # エージェント分析の抽出
        agent_analysis = None
        if "◤◢◤◢ エージェント分析 ◤◢◤◢" in response_text:
            agent_analysis = response_text.split("◤◢◤◢ エージェント分析 ◤◢◤◢")[1].split("◤◢◤◢")[0].strip()
        
        # レスポンスを保存
        chat_state.lastResponse = {
            "taskAnalysis": task_analysis,
            "gasCode": code_section,
            "explanation": explanation_section,
            "agentAnalysis": agent_analysis
        }
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # タスク分析を送信
        await update.message.reply_text(f"*◤◢◤◢ タスク分析 ◤◢◤◢*\n\n{task_analysis}", parse_mode="Markdown")
        
        # GASコードを送信
        code_message = await update.message.reply_text(f"*◤◢◤◢ GASコード生成 ◤◢◤◢*\n\n```javascript\n{code_section}\n```", parse_mode="Markdown")
        
        # コード操作ボタンを追加
        keyboard = [
            [
                InlineKeyboardButton("📋 コピー", callback_data="copy_code"),
                InlineKeyboardButton("📝 編集", callback_data="edit_code")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await code_message.edit_reply_markup(reply_markup=reply_markup)
        
        # 説明を送信
        await update.message.reply_text(f"*◤◢◤◢ 説明と次のステップ ◤◢◤◢*\n\n{explanation_section}", parse_mode="Markdown")
        
        # エージェント分析を送信（存在する場合）
        if agent_analysis:
            await update.message.reply_text(f"*◤◢◤◢ エージェント分析 ◤◢◤◢*\n\n{agent_analysis}", parse_mode="Markdown")
        
        # 実行ボタンと追加アクションボタンを表示
        if chat_state.apiKey:
            keyboard = [
                [InlineKeyboardButton("▶️ コードを実行", callback_data="execute_code")],
                [
                    InlineKeyboardButton("📊 表形式表示", callback_data="format_result_table"),
                    InlineKeyboardButton("📈 グラフ化", callback_data="visualize_data")
                ],
                [
                    InlineKeyboardButton("📚 類似例", callback_data="show_examples"),
                    InlineKeyboardButton("💾 保存", callback_data="save_code")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('次のアクションを選択してください：', reply_markup=reply_markup)
        else:
            keyboard = [
                [InlineKeyboardButton("🔑 APIキーを設定", callback_data="set_api_key")],
                [
                    InlineKeyboardButton("📚 類似例", callback_data="show_examples"),
                    InlineKeyboardButton("💾 保存", callback_data="save_code")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('コードを実行するには、APIキーを設定してください。', reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"リクエスト処理エラー: {str(e)}")
        await processing_msg.delete()
        await update.message.reply_text(f"リクエストの処理中にエラーが発生しました: {str(e)}")

# コード実行
async def execute_code(chat_id, code, chat_state):
    """コードを実行する"""
    if not chat_state.apiKey:
        await context.bot.send_message(chat_id, 'APIキーが設定されていません。')
        return
    
    # 処理中メッセージを送信
    processing_msg = await context.bot.send_message(chat_id, '🔄 コードを実行中...')
    
    try:
        # GASコード実行ツールの作成
        execute_tool = ExecuteGASCodeTool()
        
        # コードの実行
        title = chat_state.lastRequest.get("title", "GAS Script") if chat_state.lastRequest else "GAS Script"
        result = execute_tool.execute(code, title)
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # 実行結果を保存
        if chat_state.lastResponse:
            chat_state.lastResponse["executionResult"] = result
        
        # 実行結果を送信
        if result.get("success", False):
            result_text = json.dumps(result.get("result", {}), indent=2, ensure_ascii=False)
            
            # 結果が長すぎる場合は切り詰める
            if len(result_text) > 4000:
                result_text = result_text[:4000] + '...\n\n(結果が長すぎるため切り詰められました)'
            
            # 実行結果を送信
            await context.bot.send_message(
                chat_id,
                f"*◤◢◤◢ 実行結果 ◤◢◤◢*\n\n```json\n{result_text}\n```",
                parse_mode="Markdown"
            )
            
            # 分析を実行
            if chat_state.analyzeResult:
                await context.bot.send_message(chat_id, '🔍 実行結果を分析中...')
                
                # 分析ツールの作成
                analyze_tool = AnalyzeResultTool()
                
                # 分析の実行
                analysis_result = analyze_tool.analyze(result, code)
                
                # 分析結果を送信
                analysis_text = analysis_result.get("analysis", "分析結果はありません。")
                await context.bot.send_message(
                    chat_id,
                    f"*◤◢◤◢ 分析結果 ◤◢◤◢*\n\n{analysis_text}",
                    parse_mode="Markdown"
                )
            
            # 次のアクションボタンを表示
            keyboard = [
                [
                    InlineKeyboardButton("📊 データを可視化", callback_data="visualize_result"),
                    InlineKeyboardButton("📋 結果を保存", callback_data="save_result")
                ],
                [
                    InlineKeyboardButton("🔄 コードを改善", callback_data="improve_code"),
                    InlineKeyboardButton("📝 レポート作成", callback_data="create_report")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, '次のアクションを選択してください：', reply_markup=reply_markup)
        else:
            # エラーの場合
            error_text = result.get("error", "不明なエラー")
            await context.bot.send_message(
                chat_id,
                f"*◤◢◤◢ 実行エラー ◤◢◤◢*\n\n{error_text}",
                parse_mode="Markdown"
            )
            
            # エラー情報を保存
            if chat_state.lastResponse:
                chat_state.lastResponse["executionError"] = error_text
            
            # エラー修正オプションを表示
            keyboard = [
                [
                    InlineKeyboardButton("🔧 コードを修正", callback_data="fix_code"),
                    InlineKeyboardButton("❓ ヘルプを表示", callback_data="show_error_help")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, '次のアクションを選択してください：', reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"コード実行エラー: {str(e)}")
        await processing_msg.delete()
        await context.bot.send_message(chat_id, f"コードの実行中にエラーが発生しました: {str(e)}")

# メイン関数
async def main():
    """メイン関数"""
    # APIキーの確認
    if not TELEGRAM_TOKEN:
        logger.error("Error: TELEGRAM_TOKEN環境変数が設定されていません。")
        return
    
    if not OPENAI_API_KEY:
        logger.error("Error: OPENAI_API_KEY環境変数が設定されていません。")
        return
    
    # アプリケーションの作成
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # コマンドハンドラの追加
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("useagents", toggle_agents_mode))
    application.add_handler(CommandHandler("useenhancedagents", toggle_enhanced_agents_mode))
    application.add_handler(CommandHandler("analyzeresult", toggle_analyze_result_mode))
    
    # メッセージハンドラの追加
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # コールバッククエリハンドラの追加
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # エラーハンドラの追加
    application.add_error_handler(error_handler)
    
    # アプリケーションの起動
    logger.info("Telegram Botを起動しています...")
    await application.initialize()
    await application.start()
    await application.run_polling()

# エラーハンドラ
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """エラーを処理する"""
    logger.error(f"Update {update} caused error {context.error}")
    
    # エラーメッセージの送信
    if update.effective_chat:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="エラーが発生しました。しばらくしてからもう一度お試しください。"
        )

if __name__ == "__main__":
    import datetime
    asyncio.run(main())
