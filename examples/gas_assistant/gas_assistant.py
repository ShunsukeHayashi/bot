import os
import json
from typing import Dict, List, Any, Optional, Union, Literal
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# 修正: インポート文を修正
from agents import Agent, run, RunConfig, FunctionTool, ToolCallItem, OpenAIChatCompletionsModel, RunResult

# 環境変数からAPIキーを取得
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GAS_API_KEY = os.environ.get("GAS_API_KEY")
GAS_API_ENDPOINT = os.environ.get("GAS_API_ENDPOINT")

# モデル設定
MODEL_NAME = "gpt-4.1"  # または "gpt-4-turbo"

# 専門エージェントの種類
AGENT_TYPES = Literal[
    "base",
    "spreadsheet",
    "document",
    "form",
    "calendar",
    "gmail",
    "api",
    "ui",
    "optimizer"
]

# GASコード実行ツール
class ExecuteGASCodeTool(FunctionTool):
    def __init__(self):
        params_schema = {
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
        
        super().__init__(
            name="execute_gas_code",
            description="Google Apps Scriptコードを実行し、結果を返します",
            params_json_schema=params_schema,
            on_invoke_tool=self.execute
        )
    
    def execute(self, code: str, title: Optional[str] = "GAS Script") -> Dict[str, Any]:
        """
        Google Apps Scriptコードを実行し、結果を返します
        
        Args:
            code: 実行するGASコード。関数宣言を使わず、直接コードを記述し、結果をreturnで返す形式にしてください。
            title: スクリプトのタイトル（オプション）
            
        Returns:
            実行結果を含む辞書
        """
        import requests
        
        if not GAS_API_ENDPOINT or not GAS_API_KEY:
            return {
                "success": False,
                "error": "GAS API設定が見つかりません。環境変数GAS_API_ENDPOINTとGAS_API_KEYを設定してください。"
            }
        
        try:
            # APIリクエスト
            response = requests.post(
                GAS_API_ENDPOINT,
                json={
                    "title": title,
                    "script": code,
                    "apiKey": GAS_API_KEY
                },
                headers={"Content-Type": "application/json"}
            )
            
            # レスポンスの解析
            if response.status_code == 200:
                result = response.json()
                return result
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

# 分析ツール
class AnalyzeResultTool(FunctionTool):
    def __init__(self):
        params_schema = {
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
        
        super().__init__(
            name="analyze_result",
            description="GASコードの実行結果を分析し、洞察を提供します",
            params_json_schema=params_schema,
            on_invoke_tool=self.analyze
        )
    
    def analyze(self, result: Dict[str, Any], code: str) -> Dict[str, Any]:
        """
        GASコードの実行結果を分析し、洞察を提供します
        
        Args:
            result: GASコードの実行結果
            code: 実行されたGASコード
            
        Returns:
            分析結果を含む辞書
        """
        # この関数は実際にはLLMを使用して分析を行いますが、
        # ここではダミーの実装を返します
        return {
            "success": True,
            "analysis": "実行結果の分析はLLMによって行われます。"
        }

# ハンドオフツール
class HandoffTool(FunctionTool):
    def __init__(self, agent_manager):
        self.agent_manager = agent_manager
        
        params_schema = {
            "type": "object",
            "properties": {
                "agent_type": {
                    "type": "string",
                    "enum": ["base", "spreadsheet", "document", "form", "calendar", "gmail", "api", "ui", "optimizer"],
                    "description": "専門エージェントの種類"
                },
                "task": {
                    "type": "string",
                    "description": "実行するタスクの説明"
                }
            },
            "required": ["agent_type", "task"]
        }
        
        super().__init__(
            name="handoff_to_specialist",
            description="タスクを専門エージェントに引き継ぎます",
            params_json_schema=params_schema,
            on_invoke_tool=self.handoff
        )
    
    def handoff(self, agent_type: AGENT_TYPES, task: str) -> Dict[str, Any]:
        """
        タスクを専門エージェントに引き継ぎます
        
        Args:
            agent_type: 専門エージェントの種類（"spreadsheet", "document", "form", "calendar", "gmail", "api", "ui", "optimizer"）
            task: 実行するタスクの説明
            
        Returns:
            専門エージェントからの応答を含む辞書
        """
        return self.agent_manager.run_specialist_agent(agent_type, task)

# 基本エージェント
class BaseGASAgent:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.api_key = api_key
        self.tools = [ExecuteGASCodeTool(), AnalyzeResultTool()]
        
        # エージェント設定
        self.config = RunConfig(
            name="GAS Assistant",
            description="Google Apps Script専門のAIアシスタント",
            model=OpenAIChatCompletionsModel(
                model=MODEL_NAME,
                api_key=self.api_key
            ),
            tools=self.tools,
            system_prompt=self._get_system_prompt()
        )
        
        self.agent = Agent(self.config)
    
    def _get_system_prompt(self) -> str:
        return """
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
        - 必ず結果をreturn文で返す形式
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
        
        タスクが複雑な場合や、特定の専門知識が必要な場合は、専門エージェントにハンドオフすることを検討してください。
        """
    
    async def run(self, query: str) -> RunResult:
        """エージェントを実行する"""
        result = await run(self.agent, {"query": query})
        return result

# エージェントマネージャー
class GASAgentManager:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.api_key = api_key
        self.base_agent = BaseGASAgent(api_key)
        self.specialist_agents = {}
        
        # 基本エージェントにハンドオフツールを追加
        handoff_tool = HandoffTool(self)
        self.base_agent.tools.append(handoff_tool)
        
        # 設定を更新
        self.base_agent.config = RunConfig(
            name=self.base_agent.config.name,
            description=self.base_agent.config.description,
            model=self.base_agent.config.model,
            tools=self.base_agent.tools,
            system_prompt=self.base_agent.config.system_prompt
        )
        
        self.base_agent.agent = Agent(self.base_agent.config)
    
    def _get_specialist_agent(self, agent_type: AGENT_TYPES) -> Agent:
        """専門エージェントを取得または作成する"""
        if agent_type in self.specialist_agents:
            return self.specialist_agents[agent_type]
        
        # 専門エージェントのシステムプロンプト
        system_prompts = {
            "base": self.base_agent._get_system_prompt(),
            "spreadsheet": """
            あなたはGoogle Spreadsheet専門のAIアシスタントです。
            SpreadsheetAppを使用して、スプレッドシートの操作と自動化を行います。
            データの取得、加工、分析、可視化などの専門知識を持っています。
            """,
            "document": """
            あなたはGoogle Document専門のAIアシスタントです。
            DocumentAppを使用して、ドキュメントの操作と自動化を行います。
            テキスト処理、書式設定、テンプレート作成などの専門知識を持っています。
            """,
            "form": """
            あなたはGoogle Form専門のAIアシスタントです。
            FormAppを使用して、フォームの作成と応答処理を行います。
            質問設計、回答集計、条件分岐などの専門知識を持っています。
            """,
            "calendar": """
            あなたはGoogle Calendar専門のAIアシスタントです。
            CalendarAppを使用して、カレンダーの操作と自動化を行います。
            予定管理、リマインダー設定、空き時間検索などの専門知識を持っています。
            """,
            "gmail": """
            あなたはGmail専門のAIアシスタントです。
            GmailAppを使用して、メールの操作と自動化を行います。
            メール送信、検索、フィルタリング、添付ファイル処理などの専門知識を持っています。
            """,
            "api": """
            あなたはAPI連携専門のAIアシスタントです。
            UrlFetchAppを使用して、外部APIとの連携を行います。
            HTTP通信、認証、データ変換、エラーハンドリングなどの専門知識を持っています。
            """,
            "ui": """
            あなたはUI専門のAIアシスタントです。
            HtmlServiceを使用して、カスタムUIの作成を行います。
            HTML、CSS、JavaScript、Webコンポーネントなどの専門知識を持っています。
            """,
            "optimizer": """
            あなたはコード最適化専門のAIアシスタントです。
            GASコードの最適化を行います。
            パフォーマンス改善、メモリ使用量削減、実行時間短縮などの専門知識を持っています。
            """
        }
        
        # 専門エージェントの作成
        tools = [ExecuteGASCodeTool(), AnalyzeResultTool()]
        
        config = RunConfig(
            name=f"GAS {agent_type.capitalize()} Specialist",
            description=f"Google Apps Script {agent_type.capitalize()} 専門のAIアシスタント",
            model=OpenAIChatCompletionsModel(
                model=MODEL_NAME,
                api_key=self.api_key
            ),
            tools=tools,
            system_prompt=system_prompts.get(agent_type, system_prompts["base"])
        )
        
        agent = Agent(config)
        self.specialist_agents[agent_type] = agent
        return agent
    
    async def run(self, query: str) -> RunResult:
        """基本エージェントを実行する"""
        return await self.base_agent.run(query)
    
    async def run_specialist_agent(self, agent_type: AGENT_TYPES, task: str) -> Dict[str, Any]:
        """専門エージェントを実行する"""
        agent = self._get_specialist_agent(agent_type)
        result = await run(agent, {"query": task})
        
        # 結果を辞書形式に変換
        return {
            "agent_type": agent_type,
            "task": task,
            "response": result.response,
            "tool_calls": [
                {
                    "tool": tc.tool,
                    "args": tc.args,
                    "result": tcr.result if tcr else None
                }
                for tc, tcr in zip(result.tool_calls, result.tool_call_results)
            ] if result.tool_calls else []
        }

# 拡張GASエージェント
class EnhancedGASAgent:
    def __init__(self, api_key: str = OPENAI_API_KEY):
        self.api_key = api_key
        self.agent_manager = GASAgentManager(api_key)
    
    async def run(self, query: str, analyze_result: bool = False) -> Dict[str, Any]:
        """
        拡張GASエージェントを実行する
        
        Args:
            query: ユーザーのクエリ
            analyze_result: 実行結果を分析するかどうか
            
        Returns:
            実行結果を含む辞書
        """
        result = await self.agent_manager.run(query)
        
        # 結果を辞書形式に変換
        response_dict = {
            "query": query,
            "response": result.response,
            "tool_calls": []
        }
        
        # ツール呼び出しと結果を追加
        if result.tool_calls:
            for tc, tcr in zip(result.tool_calls, result.tool_call_results):
                tool_call_dict = {
                    "tool": tc.tool,
                    "args": tc.args,
                    "result": tcr.result if tcr else None
                }
                response_dict["tool_calls"].append(tool_call_dict)
                
                # GASコードの実行結果を分析
                if analyze_result and tc.tool == "execute_gas_code" and tcr and tcr.result:
                    code = tc.args.get("code", "")
                    analysis_tool = AnalyzeResultTool()
                    analysis_result = analysis_tool.analyze(tcr.result, code)
                    response_dict["analysis"] = analysis_result
        
        return response_dict

# メイン関数
async def main():
    # APIキーの確認
    print("OpenAI API Key:", OPENAI_API_KEY[:5] + "..." if OPENAI_API_KEY else None)
    print("GAS API Key:", GAS_API_KEY[:5] + "..." if GAS_API_KEY else None)
    print("GAS API Endpoint:", GAS_API_ENDPOINT[:20] + "..." if GAS_API_ENDPOINT else None)
    
    if not OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY環境変数が設定されていません。")
        return
    
    if not GAS_API_KEY or not GAS_API_ENDPOINT:
        print("Warning: GAS_API_KEYまたはGAS_API_ENDPOINT環境変数が設定されていません。")
        print("GASコードの実行はシミュレーションモードで行われます。")
    
    # エージェントの作成
    agent = EnhancedGASAgent()
    
    # デモ用のクエリ
    query = "スプレッドシートの最初の行を取得する"
    analyze = True
    
    print(f"デモクエリ: {query}")
    print(f"分析: {'有効' if analyze else '無効'}")
    
    # エージェントの実行
    result = await agent.run(query, analyze_result=analyze)
    
    # 結果の表示
    print("\n" + "="*50)
    print("応答:")
    print(result["response"])
    print("="*50)
    
    # ツール呼び出しの表示
    if result["tool_calls"]:
        print("\nツール呼び出し:")
        for i, tc in enumerate(result["tool_calls"]):
            print(f"\n--- ツール呼び出し {i+1} ---")
            print(f"ツール: {tc['tool']}")
            print(f"引数: {json.dumps(tc['args'], indent=2, ensure_ascii=False)}")
            print(f"結果: {json.dumps(tc['result'], indent=2, ensure_ascii=False) if tc['result'] else 'なし'}")
    
    # 分析結果の表示
    if "analysis" in result:
        print("\n分析結果:")
        print(json.dumps(result["analysis"], indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
