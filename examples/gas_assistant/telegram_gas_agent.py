import os
import json
import asyncio
import logging
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from io import BytesIO
from PIL import Image
import base64

# .envファイルを読み込む
load_dotenv()

# ロギングの設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# 環境変数からAPIキーを取得
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GAS_API_KEY = os.environ.get("GAS_API_KEY")
GAS_API_ENDPOINT = os.environ.get("GAS_API_ENDPOINT")

print("OpenAI API Key:", OPENAI_API_KEY[:5] + "..." if OPENAI_API_KEY else None)
print("GAS API Key:", GAS_API_KEY[:5] + "..." if GAS_API_KEY else None)
print("GAS API Endpoint:", GAS_API_ENDPOINT[:20] + "..." if GAS_API_ENDPOINT else None)
print("Telegram Token:", TELEGRAM_TOKEN[:5] + "..." if TELEGRAM_TOKEN else None)

# OpenAIクライアントの作成
client = OpenAI(api_key=OPENAI_API_KEY)

# チャットの状態
class ChatState:
    def __init__(self):
        self.state = "idle"
        self.apiKey = GAS_API_KEY
        self.lastRequest = None
        self.lastResponse = None
        self.lastImage = None
        self.messages = []
        self.savedCodes = []
        self.savedResults = []

# チャット状態の管理
chat_states = {}

# チャット状態の取得
def get_chat_state(chat_id):
    if chat_id not in chat_states:
        chat_states[chat_id] = ChatState()
        # システムプロンプトを追加
        chat_states[chat_id].messages = [
            {"role": "system", "content": system_prompt}
        ]
    return chat_states[chat_id]

# チャット状態の更新
def update_chat_state(chat_id, updates):
    chat_state = get_chat_state(chat_id)
    for key, value in updates.items():
        setattr(chat_state, key, value)
    return chat_state

# GASコード実行関数
def execute_gas_code(code: str, title: str = "GAS Script") -> Dict[str, Any]:
    """
    Google Apps Scriptコードを実行し、結果を返します
    
    Args:
        code: 実行するGASコード。関数宣言を使わず、直接コードを記述し、結果をreturnで返す形式にしてください。
        title: スクリプトのタイトル（オプション）
        
    Returns:
        実行結果を含む辞書
    """
    print(f"[DEBUG] execute_gas_code called with title: {title}")
    print(f"[DEBUG] Code to execute: {code}")
    
    if not GAS_API_ENDPOINT or not GAS_API_KEY:
        return {
            "success": False,
            "error": "GAS API設定が見つかりません。環境変数GAS_API_ENDPOINTとGAS_API_KEYを設定してください。"
        }
    
    try:
        # APIリクエスト
        import requests
        request_data = {
            "title": title,
            "script": code,
            "apiKey": GAS_API_KEY
        }
        print(f"[DEBUG] Sending request to GAS API: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            GAS_API_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"[DEBUG] Response status code: {response.status_code}")
        print(f"[DEBUG] Response headers: {response.headers}")
        print(f"[DEBUG] Response content: {response.text}")
        
        # レスポンスの解析
        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "result": result
            }
        else:
            return {
                "success": False,
                "error": f"API Error: {response.status_code} - {response.text}"
            }
    except Exception as e:
        return {
            "success": False,
            "error": f"実行エラー: {str(e)}"
        }

# データ可視化ヘルパー関数
async def visualize_numeric_data(message, data_dict, title="数値データの可視化"):
    """数値データを簡易グラフとして可視化する"""
    if not data_dict:
        return
    
    # 最大バーの長さ
    max_bar_length = 20
    
    # 最大値を取得
    max_value = max(data_dict.values())
    
    # グラフを作成
    graph = f"📊 *{title}*\n\n```\n"
    
    for key, value in data_dict.items():
        # バーの長さを計算
        bar_length = int((value / max_value) * max_bar_length) if max_value > 0 else 0
        bar = "█" * bar_length
        
        # 値の表示形式を調整
        if isinstance(value, float):
            value_str = f"{value:.2f}"
        else:
            value_str = str(value)
        
        # グラフ行を追加
        graph += f"{key.ljust(15)} | {bar.ljust(max_bar_length)} | {value_str}\n"
    
    graph += "```"
    
    await message.reply_text(graph, parse_mode="Markdown")

async def visualize_series_data(message, labels, values, title="データ系列の可視化"):
    """系列データを簡易グラフとして可視化する"""
    if not values or not labels:
        return
    
    # 最大バーの長さ
    max_bar_length = 20
    
    # 最大値と最小値を取得
    max_value = max(values)
    min_value = min(values)
    
    # グラフを作成
    graph = f"📈 *{title}*\n\n```\n"
    
    # 表示するデータ数を制限（最大10項目）
    display_limit = min(10, len(values))
    
    for i in range(display_limit):
        # バーの長さを計算
        bar_length = int(((values[i] - min_value) / (max_value - min_value if max_value > min_value else 1)) * max_bar_length)
        bar = "█" * bar_length
        
        # 値の表示形式を調整
        if isinstance(values[i], float):
            value_str = f"{values[i]:.2f}"
        else:
            value_str = str(values[i])
        
        # ラベルの表示を調整
        label = str(labels[i])
        if len(label) > 12:
            label = label[:9] + "..."
        
        # グラフ行を追加
        graph += f"{label.ljust(12)} | {bar.ljust(max_bar_length)} | {value_str}\n"
    
    # データが10項目以上ある場合
    if len(values) > 10:
        graph += f"\n... 他 {len(values) - 10} 項目（合計 {len(values)} 項目）"
    
    graph += "\n\n"
    
    # 基本的な統計情報を追加
    graph += f"最大値: {max(values):.2f if isinstance(max(values), float) else max(values)}\n"
    graph += f"最小値: {min(values):.2f if isinstance(min(values), float) else min(values)}\n"
    
    # 平均値を計算
    avg = sum(values) / len(values)
    graph += f"平均値: {avg:.2f if isinstance(avg, float) else avg}\n"
    
    graph += "```"
    
    await message.reply_text(graph, parse_mode="Markdown")

# 分析関数
def analyze_result(result: Dict[str, Any], code: str) -> Dict[str, Any]:
    """
    GASコードの実行結果を分析し、洞察を提供します
    
    Args:
        result: GASコードの実行結果
        code: 実行されたGASコード
        
    Returns:
        分析結果を含む辞書
    """
    print("[DEBUG] analyze_result called")
    print(f"[DEBUG] Result to analyze: {json.dumps(result, indent=2)}")
    print(f"[DEBUG] Code used: {code}")
    
    # この関数は実際にはLLMを使用して分析を行いますが、
    # ここではダミーの実装を返します
    return {
        "success": True,
        "analysis": "実行結果の分析はLLMによって行われます。"
    }

# ツール定義
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_gas_code",
            "description": "Google Apps Scriptコードを実行し、結果を返します",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "実行するGASコード。関数宣言を使わず、直接コードを記述し、結果をreturnで返す形式にしてください。"
                    },
                    "title": {
                        "type": "string",
                        "description": "スクリプトのタイトル（オプション）"
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_result",
            "description": "GASコードの実行結果を分析し、洞察を提供します",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "object",
                        "description": "GASコードの実行結果"
                    },
                    "code": {
                        "type": "string",
                        "description": "実行されたGASコード"
                    }
                },
                "required": ["result", "code"]
            }
        }
    }
]

# システムプロンプト
system_prompt = """
あなたはGoogle Apps Script専門のAIアシスタント「GAS Assistant」です。
Google Apps Scriptを使用して、ユーザーのタスクを実行するコードを生成し、実行します。

## 出力フォーマット

```
◤◢◤◢ タスク分析 ◤◢◤◢
[ユーザーリクエストの理解と実行計画を記述]

◤◢◤◢ GASコード生成 ◤◢◤◢
[生成したGASコードを表示]

◤◢◤◢ 実行結果 ◤◢◤◢
[コード実行の結果を構造化して表示]

◤◢◤◢ 説明と次のステップ ◤◢◤◢
[結果の解説と可能な次のアクションを提案]
```

## GASコードの特徴

- 関数宣言（function）を使わず、直接コードを記述
- 必ず結果をreturnで返す形式
- 例: `const data = SpreadsheetApp.getActiveSheet().getDataRange().getValues(); return data;`

## Google Servicesマスターリスト

- SpreadsheetApp: スプレッドシート操作
- DocumentApp: ドキュメント操作
- SlidesApp: プレゼンテーション操作
- FormApp: フォーム操作
- GmailApp: メール操作
- CalendarApp: カレンダー操作
- DriveApp: ドライブ操作
- UrlFetchApp: HTTP操作
- CacheService: キャッシュ操作
- PropertiesService: プロパティ操作
- LockService: 同時実行制御
- ScriptApp: スクリプト管理
- BigQueryApp: データ分析
- YouTubeApp: 動画管理
- Maps: 地図処理
"""

# スタートコマンドのハンドラ
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ボットを開始するコマンド"""
    chat_id = update.effective_chat.id
    
    # チャット状態の初期化
    update_chat_state(chat_id, {
        "state": "idle",
        "apiKey": GAS_API_KEY,
        "lastRequest": None,
        "lastResponse": None
    })
    
    # ウェルカムメッセージの送信
    welcome_message = """🚀 *GAS Assistant へようこそ!* 🚀

Google Apps Script専門AIアシスタントです。自然言語でリクエストを入力するだけで、GASコードを生成し、実行することができます。

*✨ 使い方:*
1️⃣ GASで実現したいことを日本語で説明してください
2️⃣ AIがタスクを分析し、GASコードを生成します
3️⃣ 必要に応じて、生成されたコードを実行できます

*📝 GASコードの特徴:*
• 関数宣言（function）を使わず、直接コードを記述
• 必ず結果をreturn文で返す形式
• 例: `const data = SpreadsheetApp.getActiveSheet().getDataRange().getValues(); return data;`

*🛠️ コマンド:*
/start - ボットを再起動
/help - ヘルプを表示
/cancel - 現在の操作をキャンセル
/settings - 設定を表示
/report - レポートを表示

*📋 サンプルリクエスト:*
• 「新しいスプレッドシートを作成して、A1セルに「Hello World」と入力してください」
• 「Gmailで未読メールを検索して、件名と送信者を一覧表示してください」
• 「カレンダーに来週の月曜日に「ミーティング」というイベントを追加してください」

*🖼️ 画像機能:*
• 画像を送信することもできます。画像と一緒にキャプションを入力すると、AIが画像を分析します。

それでは、GASで実現したいことを教えてください！"""
    
    # キーボードの作成
    keyboard = [
        [InlineKeyboardButton("📚 使い方ガイド", callback_data="show_guide")],
        [InlineKeyboardButton("🔍 サンプルを見る", callback_data="show_samples")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(welcome_message, parse_mode="Markdown", reply_markup=reply_markup)

# ヘルプコマンドのハンドラ
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ヘルプを表示するコマンド"""
    help_message = """📚 *GAS Assistant ヘルプ* 📚

*🔰 基本的な使い方:*
1️⃣ GASで実現したいことを日本語で説明してください
2️⃣ AIがタスクを分析し、GASコードを生成します
3️⃣ 生成されたコードを実行する場合は、「▶️ 実行」ボタンをクリックしてください

*⌨️ コマンド一覧:*
/start - ボットを再起動
/help - このヘルプを表示
/cancel - 現在の操作をキャンセル
/settings - 設定を表示
/report - 使用状況レポートを表示

*📝 GASコードの特徴:*
• 関数宣言（function）を使わず、直接コードを記述
• 必ず結果をreturn文で返す形式
• 例: `const data = SpreadsheetApp.getActiveSheet().getDataRange().getValues(); return data;`

*🔑 APIキーの設定:*
GASコードを実行するには、Google Apps Script APIのAPIキーが必要です。
「APIキーを設定」ボタンをクリックして設定してください。

*📊 レポート機能:*
• 使用状況レポート - GASコードの使用状況を表示
• パフォーマンスレポート - 実行時間などのパフォーマンス情報を表示
• エラーレポート - 発生したエラーの統計情報を表示

*🖼️ 画像機能:*
• 画像を送信することもできます
• 画像と一緒にキャプションを入力すると、AIが画像を分析します
• 画像から情報を抽出してGASコードを生成することも可能です

*💡 ヒント:*
• 具体的なタスクを説明すると、より良いコードが生成されます
• コードは実行前に編集することができます
• エラーが発生した場合は、詳細なエラーメッセージが表示されます"""
    
    # キーボードの作成
    keyboard = [
        [InlineKeyboardButton("🔍 サンプルリクエスト", callback_data="show_samples")],
        [InlineKeyboardButton("⚙️ 設定", callback_data="show_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(help_message, parse_mode="Markdown", reply_markup=reply_markup)

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
    api_key_status = "✅ 設定済み" if chat_state.apiKey else "❌ 未設定"
    
    # 設定メッセージの作成
    settings_message = f"""⚙️ *GAS Assistant 設定* ⚙️

*🔑 GAS APIキー:* {api_key_status}

設定を変更するには、以下のボタンを使用してください:"""
    
    # インラインキーボードの作成
    keyboard = [
        [InlineKeyboardButton("🔑 APIキーを設定", callback_data="set_api_key")],
        [InlineKeyboardButton("🔙 メインメニューに戻る", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(settings_message, reply_markup=reply_markup, parse_mode="Markdown")

# データ可視化ヘルパー関数
async def visualize_data(message, result, status_msg=None):
    """実行結果データを可視化する"""
    result_data = result.get("result", {})
    
    # データの型を確認
    if isinstance(result_data, dict):
        # 辞書型データの可視化
        formatted_data = "📊 *データ可視化結果*\n\n"
        formatted_data += "```\n"
        formatted_data += "| キー | 値 |\n"
        formatted_data += "|------|------|\n"
        
        # 数値データを収集（グラフ表示用）
        numeric_data = {}
        
        # 辞書の各項目を表形式で表示
        for key, value in result_data.items():
            # 値が複雑なオブジェクトの場合は簡略化
            if isinstance(value, (dict, list)):
                value = f"{type(value).__name__}[{len(value)}項目]"
            elif isinstance(value, (int, float)):
                # 数値データを収集
                numeric_data[key] = value
            
            formatted_data += f"| {key} | {value} |\n"
        
        formatted_data += "```"
        await message.reply_text(formatted_data, parse_mode="Markdown")
        
        # 数値データがある場合、簡易グラフを表示
        if numeric_data:
            await visualize_numeric_data(message, numeric_data, "辞書データの可視化")
    
    elif isinstance(result_data, list):
        # リスト型データの可視化
        if len(result_data) > 0:
            # リストの最初の要素が辞書かどうかを確認
            if isinstance(result_data[0], dict):
                # 表形式でデータを表示（最初の5行まで）
                formatted_data = "📊 *データ可視化結果（テーブル形式）*\n\n"
                formatted_data += "```\n"
                
                # ヘッダー行の作成
                keys = list(result_data[0].keys())
                header = "| " + " | ".join(keys) + " |\n"
                separator = "|" + "|".join(["------" for _ in keys]) + "|\n"
                
                formatted_data += header + separator
                
                # データ行の作成（最大5行）
                for i, item in enumerate(result_data[:5]):
                    row_values = []
                    for key in keys:
                        value = item.get(key, "")
                        # 複雑な値は簡略化
                        if isinstance(value, (dict, list)):
                            value = f"{type(value).__name__}[{len(value)}項目]"
                        row_values.append(str(value))
                    
                    formatted_data += "| " + " | ".join(row_values) + " |\n"
                
                # データが5行以上ある場合
                if len(result_data) > 5:
                    formatted_data += f"\n... 他 {len(result_data) - 5} 行のデータ（合計 {len(result_data)} 行）"
                
                formatted_data += "```"
                await message.reply_text(formatted_data, parse_mode="Markdown")
                
                # 数値データの列を特定してグラフ化
                numeric_columns = {}
                for key in keys:
                    # 最初の要素が数値かどうかを確認
                    if isinstance(result_data[0].get(key), (int, float)):
                        numeric_columns[key] = [item.get(key, 0) for item in result_data if isinstance(item.get(key), (int, float))]
                
                # 数値データの列があれば可視化
                if numeric_columns:
                    for column_name, values in numeric_columns.items():
                        if values:  # 空でない場合のみ可視化
                            labels = [f"行{i+1}" for i in range(len(values))]
                            await visualize_series_data(message, labels, values, f"{column_name}の推移")
            else:
                # 単純なリストの場合
                formatted_data = "📊 *データ可視化結果（リスト形式）*\n\n"
                formatted_data += "```\n"
                
                # 最大10項目まで表示
                for i, item in enumerate(result_data[:10]):
                    formatted_data += f"{i+1}. {item}\n"
                
                # データが10項目以上ある場合
                if len(result_data) > 10:
                    formatted_data += f"\n... 他 {len(result_data) - 10} 項目（合計 {len(result_data)} 項目）"
                
                formatted_data += "```"
                await message.reply_text(formatted_data, parse_mode="Markdown")
                
                # すべての要素が数値の場合、グラフ表示
                if all(isinstance(item, (int, float)) for item in result_data):
                    labels = [f"項目{i+1}" for i in range(len(result_data))]
                    await visualize_series_data(message, labels, result_data, "数値データの可視化")
        else:
            await message.reply_text('⚠️ リストは空です。データがありません。')
    
    else:
        # その他のデータ型（文字列、数値など）
        formatted_data = f"📊 *データ可視化結果*\n\n```\n{result_data}\n```"
        await message.reply_text(formatted_data, parse_mode="Markdown")
    
    # 追加の操作ボタンを表示
    keyboard = [
        [InlineKeyboardButton("🔍 詳細分析", callback_data="action:analyze:data")],
        [
            InlineKeyboardButton("🔄 コードを改善", callback_data="action:improve:code"),
            InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if status_msg:
        await status_msg.edit_text('他のアクションを選択できます：')
        await status_msg.edit_reply_markup(reply_markup=reply_markup)
    else:
        status_msg = await message.reply_text('他のアクションを選択できます：')
        await status_msg.edit_reply_markup(reply_markup=reply_markup)

# レポートアクションハンドラ
async def handle_report_action(update, context, report_type, item_id=None):
    """レポートアクションを処理する"""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    # 処理中メッセージを表示
    status_msg = await query.message.reply_text(f'📊 {report_type}レポートを生成中...')
    
    try:
        # gas_report_generator モジュールをインポート
        from gas_report_generator import generate_report, get_available_reports
        
        if report_type == "list":
            # 利用可能なレポート一覧を表示
            reports = get_available_reports()
            
            report_list = "📊 *利用可能なレポート*\n\n"
            for i, report in enumerate(reports):
                report_list += f"{i+1}. {report['name']} - {report['description']}\n"
            
            await status_msg.edit_text(report_list, parse_mode="Markdown")
            
            # レポート選択ボタンを表示
            keyboard = []
            for report in reports:
                keyboard.append([InlineKeyboardButton(f"📊 {report['name']}",
                                                    callback_data=f"action:report:generate:{report['id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 戻る", callback_data="action:new_request")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_reply_markup(reply_markup=reply_markup)
            
        elif report_type == "generate":
            # 指定されたレポートを生成
            report_data = await generate_report(item_id)
            
            if report_data.get("success", False):
                # レポートの表示
                await _send_report(update, context, report_data, status_msg)
            else:
                await status_msg.edit_text(f"⚠️ レポート生成エラー: {report_data.get('error', '不明なエラー')}")
                
                # 再試行ボタンを表示
                keyboard = [
                    [InlineKeyboardButton("🔄 再試行", callback_data=f"action:report:generate:{item_id}")],
                    [InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_msg.edit_reply_markup(reply_markup=reply_markup)
        
        else:
            await status_msg.edit_text(f"⚠️ 不明なレポートタイプ: {report_type}")
    
    except ImportError:
        await status_msg.edit_text("⚠️ レポート機能が利用できません。gas_report_generator モジュールが見つかりません。")
    except Exception as e:
        logger.error(f"レポート処理エラー: {str(e)}")
        await status_msg.edit_text(f"⚠️ レポート処理中にエラーが発生しました: {str(e)}")

# レポート表示関数
async def _send_report(update, context, report_data, status_msg=None):
    """レポートを表示する"""
    query = update.callback_query
    chat_id = query.message.chat_id
    
    report = report_data.get("report", {})
    report_type = report.get("type", "text")
    report_title = report.get("title", "レポート")
    report_content = report.get("content", "データがありません")
    
    if status_msg:
        await status_msg.delete()
    
    # レポートタイプに応じた表示
    if report_type == "text":
        # テキストレポート
        await query.message.reply_text(f"📊 *{report_title}*\n\n{report_content}", parse_mode="Markdown")
    
    elif report_type == "table":
        # テーブルレポート
        table_data = report.get("data", [])
        if table_data:
            formatted_data = f"📊 *{report_title}*\n\n"
            formatted_data += "```\n"
            
            # ヘッダー行の作成
            headers = report.get("headers", list(table_data[0].keys()))
            header = "| " + " | ".join(headers) + " |\n"
            separator = "|" + "|".join(["------" for _ in headers]) + "|\n"
            
            formatted_data += header + separator
            
            # データ行の作成
            for row in table_data:
                row_values = []
                for header in headers:
                    value = row.get(header, "")
                    row_values.append(str(value))
                
                formatted_data += "| " + " | ".join(row_values) + " |\n"
            
            formatted_data += "```"
            await query.message.reply_text(formatted_data, parse_mode="Markdown")
        else:
            await query.message.reply_text(f"📊 *{report_title}*\n\nデータがありません")
    
    elif report_type == "chart":
        # チャートレポート
        chart_data = report.get("data", {})
        if chart_data:
            await _send_chart(query.message, chart_data, report_title)
        else:
            await query.message.reply_text(f"📊 *{report_title}*\n\nチャートデータがありません")
    
    # 追加のアクションボタンを表示
    keyboard = [
        [InlineKeyboardButton("📊 他のレポートを見る", callback_data="action:report:list")],
        [InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    status_msg = await query.message.reply_text('他のアクションを選択できます：')
    await status_msg.edit_reply_markup(reply_markup=reply_markup)

# チャート表示関数
async def _send_chart(message, chart_data, title):
    """チャートを表示する"""
    chart_type = chart_data.get("type", "bar")
    
    if chart_type == "bar":
        # 棒グラフ
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        
        if labels and values:
            await visualize_series_data(message, labels, values, title)
        else:
            await message.reply_text(f"📊 *{title}*\n\nチャートデータが不完全です")
    
    elif chart_type == "pie":
        # 円グラフ（簡易表示）
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        
        if labels and values:
            # 辞書形式に変換
            pie_data = {label: value for label, value in zip(labels, values)}
            await visualize_numeric_data(message, pie_data, title)
        else:
            await message.reply_text(f"📊 *{title}*\n\nチャートデータが不完全です")

# コールバッククエリのハンドラ
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """コールバッククエリを処理する"""
    query = update.callback_query
    
    chat_id = query.message.chat_id
    chat_state = get_chat_state(chat_id)
    data = query.data
    
    # 処理中の通知を表示
    await query.answer("処理中...")
    
    # 現在のメッセージのボタンを削除（クリーンな表示のため）
    try:
        await query.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.error(f"ボタン削除エラー: {str(e)}")
    
    # コールバックデータが「:」で区切られている場合（例：action:subaction:id）
    if ":" in data and data.startswith("action:"):
        parts = data.split(":")
        action = parts[1] if len(parts) > 1 else None
        subaction = parts[2] if len(parts) > 2 else None
        item_id = parts[3] if len(parts) > 3 else None
        
        # 実行アクション
        if action == "execute":
            # 処理中メッセージを表示
            status_msg = await query.message.reply_text('⏳ リクエストを処理中...')
            
            if subaction == "code":
                if chat_state.lastResponse and "gasCode" in chat_state.lastResponse:
                    await execute_code(update, context, chat_id, chat_state.lastResponse["gasCode"])
                    # 処理完了メッセージを削除
                    await status_msg.delete()
                else:
                    await status_msg.edit_text('⚠️ 実行するコードがありません。まずはGASで実現したいことを教えてください。')
                    
                    # 新しいリクエストボタンを表示
                    keyboard = [
                        [InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await status_msg.edit_reply_markup(reply_markup=reply_markup)
            return
        
        # 編集アクション
        elif action == "edit":
            if subaction == "code":
                # コード編集モードに移行
                update_chat_state(chat_id, {"state": "waiting_for_code_edit"})
                await query.message.reply_text('📝 編集したいコードを入力してください。現在のコードを送信します：')
                
                if chat_state.lastResponse and "gasCode" in chat_state.lastResponse:
                    code_msg = await query.message.reply_text(f"```javascript\n{chat_state.lastResponse['gasCode']}\n```", parse_mode="Markdown")
                    
                    # キャンセルボタンを表示
                    keyboard = [
                        [InlineKeyboardButton("❌ 編集をキャンセル", callback_data="action:cancel:edit")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await code_msg.edit_reply_markup(reply_markup=reply_markup)
                else:
                    status_msg = await query.message.reply_text('⚠️ 編集するコードがありません。')
                    
                    # 新しいリクエストボタンを表示
                    keyboard = [
                        [InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await status_msg.edit_reply_markup(reply_markup=reply_markup)
            return
        
        # 可視化アクション
        elif action == "visualize":
            if subaction == "result":
                # 処理中メッセージを表示
                status_msg = await query.message.reply_text('📊 データの可視化を準備中...')
                
                if chat_state.lastResponse and "executionResult" in chat_state.lastResponse:
                    result = chat_state.lastResponse["executionResult"]
                    if result.get("success", False):
                        await visualize_data(query.message, result, status_msg)
                    else:
                        await status_msg.edit_text('⚠️ 可視化するデータがありません。まずはコードを実行してください。')
                        
                        # 次のアクションボタンを表示
                        keyboard = [
                            [
                                InlineKeyboardButton("▶️ 実行", callback_data="action:execute:code"),
                                InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")
                            ]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        await status_msg.edit_reply_markup(reply_markup=reply_markup)
                else:
                    await status_msg.edit_text('⚠️ 可視化するデータがありません。まずはコードを実行してください。')
                    
                    # 次のアクションボタンを表示
                    keyboard = [
                        [
                            InlineKeyboardButton("▶️ 実行", callback_data="action:execute:code"),
                            InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await status_msg.edit_reply_markup(reply_markup=reply_markup)
            return
        
        # レポートアクション
        elif action == "report":
            # レポートタイプに基づいて処理
            await handle_report_action(update, context, subaction, item_id)
            return
        
        # 新しいリクエストアクション
        elif action == "new_request":
            # 新しいリクエストの準備
            update_chat_state(chat_id, {"state": "idle"})
            status_msg = await query.message.reply_text('📝 新しいリクエストを入力してください。GASで実現したいことを教えてください。')
            
            # サンプルリクエストボタンを表示
            keyboard = [
                [InlineKeyboardButton("🔍 サンプルを見る", callback_data="action:show:samples")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_reply_markup(reply_markup=reply_markup)
            return
        
        # キャンセルアクション
        elif action == "cancel":
            if subaction == "edit":
                # コード編集をキャンセル
                update_chat_state(chat_id, {"state": "idle"})
                status_msg = await query.message.reply_text('✅ コード編集をキャンセルしました。')
                
                # 次のアクションボタンを表示
                keyboard = [
                    [
                        InlineKeyboardButton("▶️ 実行", callback_data="action:execute:code"),
                        InlineKeyboardButton("📝 新しいリクエスト", callback_data="action:new_request")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await status_msg.edit_reply_markup(reply_markup=reply_markup)
            return
        
        # 表示アクション
        elif action == "show":
            if subaction == "samples":
                # サンプルリクエストを表示
                samples_message = """🔍 *サンプルリクエスト* 🔍

以下のサンプルをクリックすると、そのリクエストを送信できます:"""
                
                # サンプルリクエストのキーボードを作成
                keyboard = [
                    [InlineKeyboardButton("📊 新しいスプレッドシートを作成", callback_data="sample_create_sheet")],
                    [InlineKeyboardButton("📧 未読メールを検索", callback_data="sample_search_emails")],
                    [InlineKeyboardButton("📅 カレンダーにイベントを追加", callback_data="sample_add_event")],
                    [InlineKeyboardButton("📝 フォームを作成", callback_data="sample_create_form")],
                    [InlineKeyboardButton("🔙 メインメニューに戻る", callback_data="action:back:main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(samples_message, parse_mode="Markdown", reply_markup=reply_markup)
            
            elif subaction == "guide":
                # 使い方ガイドを表示
                guide_message = """📚 *GAS Assistant 使い方ガイド* 📚

*🔰 基本的な使い方:*
1️⃣ GASで実現したいことを日本語で説明してください
2️⃣ AIがタスクを分析し、GASコードを生成します
3️⃣ 生成されたコードを実行する場合は、「▶️ 実行」ボタンをクリックしてください

*💡 効果的なリクエストのコツ:*
• 具体的なタスクを説明する（例：「スプレッドシートにデータを入力する」）
• 必要な情報を提供する（例：「シート名は'データ'です」）
• 期待する結果を明確にする（例：「結果をJSONで返してほしい」）

*🛠️ コード操作:*
• ▶️ 実行: 生成されたコードを実行します
• 📝 編集: コードを編集できます
• 📊 データを可視化: 実行結果を視覚化します
• 🔄 コードを改善: AIにコードの改善を依頼します
• 📊 レポート: 使用状況やパフォーマンスのレポートを表示します"""
                
                # キーボードの作成
                keyboard = [
                    [InlineKeyboardButton("🔙 メインメニューに戻る", callback_data="action:back:main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(guide_message, parse_mode="Markdown", reply_markup=reply_markup)
            return
        
        # 戻るアクション
        elif action == "back":
            if subaction == "main":
                # メインメニューに戻る
                keyboard = [
                    [InlineKeyboardButton("📚 使い方ガイド", callback_data="action:show:guide")],
                    [InlineKeyboardButton("🔍 サンプルを見る", callback_data="action:show:samples")],
                    [InlineKeyboardButton("📊 レポートを見る", callback_data="action:report:list")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text("🚀 *GAS Assistant* 🚀\n\nGASで実現したいことを教えてください！", parse_mode="Markdown", reply_markup=reply_markup)
            return
    
    # 通常のコールバックデータ処理（後方互換性のため）
    if data == "set_api_key":
        # APIキー設定モードに移行
        update_chat_state(chat_id, {"state": "waiting_for_api_key"})
        await query.message.reply_text('🔑 Google Apps Script APIのAPIキーを入力してください:')
    
    # 通常のコールバックデータ処理
    if data == "set_api_key":
        # APIキー設定モードに移行
        update_chat_state(chat_id, {"state": "waiting_for_api_key"})
        await query.message.reply_text('🔑 Google Apps Script APIのAPIキーを入力してください:')
    
    elif data == "execute_code":
        # コードを実行
        if chat_state.lastResponse and "gasCode" in chat_state.lastResponse:
            await execute_code(update, context, chat_id, chat_state.lastResponse["gasCode"])
        else:
            status_msg = await query.message.reply_text('⚠️ 実行するコードがありません。まずはGASで実現したいことを教えてください。')
            
            # 新しいリクエストボタンを表示
            keyboard = [
                [InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_reply_markup(reply_markup=reply_markup)
    
    elif data == "copy_code":
        # コードがコピーされたことを通知
        status_msg = await query.message.reply_text('✅ コードをクリップボードにコピーしました。')
        
        # 次のアクションボタンを表示
        keyboard = [
            [
                InlineKeyboardButton("▶️ 実行", callback_data="execute_code"),
                InlineKeyboardButton("📝 編集", callback_data="edit_code")
            ],
            [
                InlineKeyboardButton("🔄 改善", callback_data="improve_code"),
                InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_reply_markup(reply_markup=reply_markup)
    
    elif data == "edit_code":
        # コード編集モードに移行
        update_chat_state(chat_id, {"state": "waiting_for_code_edit"})
        await query.message.reply_text('📝 編集したいコードを入力してください。現在のコードを送信します：')
        
        if chat_state.lastResponse and "gasCode" in chat_state.lastResponse:
            code_msg = await query.message.reply_text(f"```javascript\n{chat_state.lastResponse['gasCode']}\n```", parse_mode="Markdown")
            
            # キャンセルボタンを表示
            keyboard = [
                [InlineKeyboardButton("❌ 編集をキャンセル", callback_data="cancel_edit")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await code_msg.edit_reply_markup(reply_markup=reply_markup)
        else:
            status_msg = await query.message.reply_text('⚠️ 編集するコードがありません。')
            
            # 新しいリクエストボタンを表示
            keyboard = [
                [InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await status_msg.edit_reply_markup(reply_markup=reply_markup)
    
    elif data == "cancel_edit":
        # コード編集をキャンセル
        update_chat_state(chat_id, {"state": "idle"})
        status_msg = await query.message.reply_text('✅ コード編集をキャンセルしました。')
        
        # 次のアクションボタンを表示
        keyboard = [
            [
                InlineKeyboardButton("▶️ 実行", callback_data="execute_code"),
                InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await status_msg.edit_reply_markup(reply_markup=reply_markup)
    
    elif data == "new_request":
        # 新しいコールバックデータ形式にリダイレクト
        new_query = update.callback_query
        new_query.data = "action:new_request"
        await handle_callback_query(update, context)
    
    elif data == "visualize_result":
        # 新しいコールバックデータ形式にリダイレクト
        new_query = update.callback_query
        new_query.data = "action:visualize:result"
        await handle_callback_query(update, context)
    
    elif data == "show_guide":
        # 使い方ガイドを表示
        guide_message = """📚 *GAS Assistant 使い方ガイド* 📚

*🔰 基本的な使い方:*
1️⃣ GASで実現したいことを日本語で説明してください
2️⃣ AIがタスクを分析し、GASコードを生成します
3️⃣ 生成されたコードを実行する場合は、「▶️ 実行」ボタンをクリックしてください

*💡 効果的なリクエストのコツ:*
• 具体的なタスクを説明する（例：「スプレッドシートにデータを入力する」）
• 必要な情報を提供する（例：「シート名は'データ'です」）
• 期待する結果を明確にする（例：「結果をJSONで返してほしい」）

*🛠️ コード操作:*
• ▶️ 実行: 生成されたコードを実行します
• 📝 編集: コードを編集できます
• 📊 データを可視化: 実行結果を視覚化します
• 🔄 コードを改善: AIにコードの改善を依頼します"""
        
        # キーボードの作成
        keyboard = [
            [InlineKeyboardButton("🔙 メインメニューに戻る", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(guide_message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "show_samples":
        # サンプルリクエストを表示
        samples_message = """🔍 *サンプルリクエスト* 🔍

以下のサンプルをクリックすると、そのリクエストを送信できます:"""
        
        # サンプルリクエストのキーボードを作成
        keyboard = [
            [InlineKeyboardButton("📊 新しいスプレッドシートを作成", callback_data="sample_create_sheet")],
            [InlineKeyboardButton("📧 未読メールを検索", callback_data="sample_search_emails")],
            [InlineKeyboardButton("📅 カレンダーにイベントを追加", callback_data="sample_add_event")],
            [InlineKeyboardButton("📝 フォームを作成", callback_data="sample_create_form")],
            [InlineKeyboardButton("🔙 メインメニューに戻る", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(samples_message, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "back_to_main":
        # メインメニューに戻る
        keyboard = [
            [InlineKeyboardButton("📚 使い方ガイド", callback_data="show_guide")],
            [InlineKeyboardButton("🔍 サンプルを見る", callback_data="show_samples")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text("🚀 *GAS Assistant* 🚀\n\nGASで実現したいことを教えてください！", parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "show_settings":
        # 設定を表示
        await settings(update, context)
    
    elif data == "sample_create_sheet":
        # サンプルリクエスト: スプレッドシート作成
        # 新しいメッセージを作成してprocess_requestに渡す
        message = types.SimpleNamespace()
        message.text = "新しいスプレッドシートを作成して、A1セルに「Hello World」と入力してください"
        message.reply_text = query.message.reply_text
        update_obj = types.SimpleNamespace()
        update_obj.message = message
        update_obj.effective_chat = query.message.chat
        await process_request(update_obj, context)
    
    elif data == "sample_search_emails":
        # サンプルリクエスト: メール検索
        message = types.SimpleNamespace()
        message.text = "Gmailで未読メールを検索して、件名と送信者を一覧表示してください"
        message.reply_text = query.message.reply_text
        update_obj = types.SimpleNamespace()
        update_obj.message = message
        update_obj.effective_chat = query.message.chat
        await process_request(update_obj, context)
    
    elif data == "sample_add_event":
        # サンプルリクエスト: カレンダーイベント追加
        message = types.SimpleNamespace()
        message.text = "カレンダーに来週の月曜日に「ミーティング」というイベントを追加してください"
        message.reply_text = query.message.reply_text
        update_obj = types.SimpleNamespace()
        update_obj.message = message
        update_obj.effective_chat = query.message.chat
        await process_request(update_obj, context)
    
    elif data == "sample_create_form":
        # サンプルリクエスト: フォーム作成
        message = types.SimpleNamespace()
        message.text = "「顧客アンケート」というタイトルのフォームを作成し、名前、メール、満足度（5段階）の質問を追加してください"
        message.reply_text = query.message.reply_text
        update_obj = types.SimpleNamespace()
        update_obj.message = message
        update_obj.effective_chat = query.message.chat
        await process_request(update_obj, context)

# コード実行
async def execute_code(update, context, chat_id, code):
    """コードを実行する"""
    chat_state = get_chat_state(chat_id)
    
    if not chat_state.apiKey:
        # APIキーが設定されていない場合、設定を促す
        keyboard = [
            [InlineKeyboardButton("🔑 APIキーを設定", callback_data="set_api_key")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id, 
            '⚠️ *APIキーが設定されていません*\n\nGASコードを実行するには、Google Apps Script APIのAPIキーが必要です。「APIキーを設定」ボタンをクリックして設定してください。',
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return
    
    # 処理中メッセージを送信（アニメーション付き）
    processing_msg = await context.bot.send_message(chat_id, '⏳ コードを実行中...')
    
    try:
        # コードの実行
        title = "GAS Script"
        if chat_state.lastRequest:
            title = chat_state.lastRequest.get("title", "GAS Script")
        
        result = execute_gas_code(code, title)
        
        # 処理中メッセージを削除
        await processing_msg.delete()
        
        # 実行結果を保存
        if "lastResponse" in chat_state.__dict__ and chat_state.lastResponse:
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
                f"✅ *実行結果*\n\n```json\n{result_text}\n```",
                parse_mode="Markdown"
            )
            
            # 次のアクションボタンを表示
            keyboard = [
                [
                    InlineKeyboardButton("📊 データを可視化", callback_data="visualize_result"),
                    InlineKeyboardButton("💾 結果を保存", callback_data="save_result")
                ],
                [
                    InlineKeyboardButton("🔄 コードを改善", callback_data="improve_code"),
                    InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, '次のアクションを選択してください：', reply_markup=reply_markup)
        else:
            # エラーの場合
            error_text = result.get("error", "不明なエラー")
            await context.bot.send_message(
                chat_id,
                f"❌ *実行エラー*\n\n{error_text}",
                parse_mode="Markdown"
            )
            
            # エラー情報を保存
            if "lastResponse" in chat_state.__dict__ and chat_state.lastResponse:
                chat_state.lastResponse["executionError"] = error_text
            
            # エラー修正オプションを表示
            keyboard = [
                [
                    InlineKeyboardButton("🔧 コードを修正", callback_data="edit_code"),
                    InlineKeyboardButton("🔄 AIに修正を依頼", callback_data="fix_code")
                ],
                [
                    InlineKeyboardButton("❓ エラーの説明", callback_data="explain_error"),
                    InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(chat_id, '次のアクションを選択してください：', reply_markup=reply_markup)
    
    except Exception as e:
        logger.error(f"コード実行エラー: {str(e)}")
        await processing_msg.delete()
        await context.bot.send_message(chat_id, f"コードの実行中にエラーが発生しました: {str(e)}")

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
        if "lastResponse" in chat_state.__dict__ and chat_state.lastResponse:
            # 編集されたコードを保存
            updated_response = chat_state.lastResponse.copy()
            updated_response["gasCode"] = update.message.text
            
            update_chat_state(chat_id, {
                "lastResponse": updated_response,
                "state": "idle"
            })
            
            # 編集完了メッセージと実行ボタンを表示
            keyboard = [
                [InlineKeyboardButton("▶️ 編集したコードを実行", callback_data="execute_code")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('✅ コードを編集しました。', reply_markup=reply_markup)
        else:
            update_chat_state(chat_id, {"state": "idle"})
            await update.message.reply_text('❌ コードの編集に失敗しました。新しいリクエストを送信してください。')
    
    else:
        # 通常のリクエスト処理
        await process_request(update, context)

# リクエスト処理
async def process_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """リクエストを処理する"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    content = update.message.text
    logger.debug(f"Processing request from chat_id {chat_id}: {content}")
    
    # 処理中メッセージを送信（アニメーション付き）
    processing_msg = await update.message.reply_text('🧠 リクエストを分析中...')
    
    # タイトルを生成（内容の最初の10単語程度）
    title = " ".join(content.split()[:10])
    
    # リクエストを保存
    chat_state.lastRequest = {
        "title": title,
        "content": content
    }
    
    # ユーザーメッセージを追加
    chat_state.messages.append({"role": "user", "content": content})
    
    try:
        # 応答ループ
        while True:
            # APIリクエスト
            logger.debug("Creating chat completion with OpenAI")
            logger.debug(f"Messages: {json.dumps(chat_state.messages, indent=2)}")
            logger.debug(f"Tools: {json.dumps(tools, indent=2)}")
            
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=chat_state.messages,
                tools=tools,
                tool_choice="auto"
            )
            
            # レスポンスの処理
            response_message = response.choices[0].message
            chat_state.messages.append(response_message.dict())
            
            # ツール呼び出しの処理
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    
                    if function_name == "execute_gas_code":
                        # 引数の解析
                        args = json.loads(tool_call.function.arguments)
                        code = args.get("code")
                        title = args.get("title", "GAS Script")
                        
                        # ツールの実行
                        result = execute_gas_code(code, title)
                        
                    elif function_name == "analyze_result":
                        # 引数の解析
                        args = json.loads(tool_call.function.arguments)
                        result_to_analyze = args.get("result")
                        code = args.get("code")
                        
                        # ツールの実行
                        result = analyze_result(result_to_analyze, code)
                    
                    # 結果をメッセージに追加
                    chat_state.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": function_name,
                        "content": json.dumps(result)
                    })
                
                # 続けて応答を取得
                continue
            
            # 処理中メッセージを削除
            await processing_msg.delete()
            
            # レスポンスからコードと説明を抽出
            response_text = response_message.content
            
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
            
            # レスポンスを保存
            chat_state.lastResponse = {
                "taskAnalysis": task_analysis,
                "gasCode": code_section,
                "explanation": explanation_section
            }
            
            # タスク分析を送信
            if task_analysis:
                await update.message.reply_text(f"🔍 *タスク分析*\n\n{task_analysis}", parse_mode="Markdown")
            
            # GASコードを送信
            if code_section:
                code_message = await update.message.reply_text(f"💻 *GASコード*\n\n```javascript\n{code_section}\n```", parse_mode="Markdown")
                
                # コード操作ボタンを追加
                keyboard = [
                    [
                        InlineKeyboardButton("▶️ 実行", callback_data="execute_code"),
                        InlineKeyboardButton("📝 編集", callback_data="edit_code")
                    ],
                    [
                        InlineKeyboardButton("📋 コピー", callback_data="copy_code"),
                        InlineKeyboardButton("🔄 改善", callback_data="improve_code")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                await code_message.edit_reply_markup(reply_markup=reply_markup)
            
            # 説明を送信
            if explanation_section:
                # 説明メッセージと次のアクションボタンを表示
                keyboard = [
                    [InlineKeyboardButton("📝 新しいリクエスト", callback_data="new_request")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"📝 *説明と次のステップ*\n\n{explanation_section}", 
                    parse_mode="Markdown",
                    reply_markup=reply_markup
                )
            
            # コードがない場合は全体のレスポンスを送信
            if not code_section and not task_analysis and not explanation_section:
                await update.message.reply_text(response_text)
            
            break
    
    except Exception as e:
        logger.error(f"リクエスト処理エラー: {str(e)}")
        await processing_msg.delete()
        await update.message.reply_text(f"リクエストの処理中にエラーが発生しました: {str(e)}")

# 拡張機能コマンドハンドラ
async def use_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """エージェント機能を使用するコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # エージェント機能を有効化
    update_chat_state(chat_id, {"use_agents": True})
    
    await update.message.reply_text(
        "🤖 *エージェント機能が有効になりました*\n\n"
        "複数のAIエージェントが協力してタスクを処理します。"
        "より複雑なタスクや分析が可能になります。",
        parse_mode="Markdown"
    )

async def use_enhanced_agents(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """拡張エージェント機能を使用するコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    # 拡張エージェント機能を有効化
    update_chat_state(chat_id, {
        "use_agents": True,
        "use_enhanced_agents": True
    })
    
    await update.message.reply_text(
        "🚀 *拡張エージェント機能が有効になりました*\n\n"
        "高度な分析能力と専門知識を持つエージェントが協力してタスクを処理します。"
        "データ分析、コード最適化、ビジュアライゼーションなどの機能が強化されます。",
        parse_mode="Markdown"
    )

async def analyze_result_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """実行結果を分析するコマンド"""
    chat_id = update.effective_chat.id
    chat_state = get_chat_state(chat_id)
    
    if not chat_state.lastResponse or "executionResult" not in chat_state.lastResponse:
        await update.message.reply_text(
            "⚠️ 分析する実行結果がありません。まずはコードを実行してください。"
        )
        return
    
    result = chat_state.lastResponse["executionResult"]
    code = chat_state.lastResponse.get("gasCode", "")
    
    if not result.get("success", False):
        await update.message.reply_text(
            "⚠️ 実行結果にエラーがあります。正常に実行されたコードの結果のみ分析できます。"
        )
        return
    
    # 処理中メッセージを送信
    processing_msg = await update.message.reply_text('🔍 実行結果を分析中...')
    
    try:
        # 分析を実行
        analysis_result = analyze_result(result, code)
        
        if analysis_result.get("success", False):
            # 分析結果を送信
            analysis_text = analysis_result.get("analysis", "分析結果がありません。")
            
            await processing_msg.delete()
            await update.message.reply_text(
                f"📊 *実行結果の分析*\n\n{analysis_text}",
                parse_mode="Markdown"
            )
            
            # 追加のアクションボタンを表示
            keyboard = [
                [InlineKeyboardButton("📊 データを可視化", callback_data="visualize_result")],
                [InlineKeyboardButton("🔄 コードを改善", callback_data="improve_code")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('他のアクションを選択できます：', reply_markup=reply_markup)
        else:
            await processing_msg.delete()
            await update.message.reply_text(
                f"⚠️ 分析中にエラーが発生しました: {analysis_result.get('error', '不明なエラー')}"
            )
    except Exception as e:
        logger.error(f"分析エラー: {str(e)}")
        await processing_msg.delete()
        await update.message.reply_text(f"分析中にエラーが発生しました: {str(e)}")

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

# メイン関数
async def main():
    """メイン関数"""
    logger.debug("Starting Telegram bot in DEBUG mode")
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
    
    # 拡張機能コマンドハンドラの追加
    application.add_handler(CommandHandler("useagents", use_agents))
    application.add_handler(CommandHandler("useenhancedagents", use_enhanced_agents))
    application.add_handler(CommandHandler("analyzeresult", analyze_result_command))
    
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
    
    # run_pollingの代わりにupdate_fetcherを直接実行
    # これにより、イベントループを閉じる処理が行われなくなる
    await application.updater.start_polling()

# メイン関数の実行
if __name__ == "__main__":
    # 新しいイベントループを作成して使用
    try:
        # 新しいイベントループを作成
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 非同期関数を実行
        loop.run_until_complete(main())
        
        # イベントループを実行し続ける
        loop.run_forever()
    except KeyboardInterrupt:
        # Ctrl+Cで終了した場合
        print("ボットを終了します...")
    except Exception as e:
        logger.error(f"イベントループエラー: {str(e)}")
        print(f"イベントループエラー: {str(e)}")
