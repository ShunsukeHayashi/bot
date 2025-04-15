import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import base64

# ロギングの設定
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# レポートタイプの定義
REPORT_TYPES = {
    "usage": {
        "id": "usage",
        "name": "使用状況レポート",
        "description": "GASコードの使用状況に関するレポートを生成します"
    },
    "performance": {
        "id": "performance",
        "name": "パフォーマンスレポート",
        "description": "GASコードの実行パフォーマンスに関するレポートを生成します"
    },
    "error": {
        "id": "error",
        "name": "エラーレポート",
        "description": "GASコードの実行エラーに関するレポートを生成します"
    },
    "summary": {
        "id": "summary",
        "name": "サマリーレポート",
        "description": "GASコードの使用状況、パフォーマンス、エラーの概要を表示します"
    }
}

# 利用可能なレポート一覧を取得
def get_available_reports() -> List[Dict[str, str]]:
    """利用可能なレポート一覧を返します"""
    return list(REPORT_TYPES.values())

# レポートデータの保存先
def get_report_data_path() -> str:
    """レポートデータの保存先を返します"""
    # 現在のディレクトリにreport_dataフォルダを作成
    data_dir = os.path.join(os.path.dirname(__file__), "report_data")
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

# レポートデータの保存
def save_execution_data(execution_data: Dict[str, Any]) -> None:
    """実行データを保存します"""
    try:
        data_dir = get_report_data_path()
        
        # 現在の日付をファイル名に使用
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = os.path.join(data_dir, f"execution_data_{today}.json")
        
        # 既存のデータを読み込む
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        
        # 新しいデータを追加
        execution_data["timestamp"] = datetime.now().isoformat()
        existing_data.append(execution_data)
        
        # データを保存
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"実行データを保存しました: {file_path}")
    except Exception as e:
        logger.error(f"実行データの保存中にエラーが発生しました: {str(e)}")

# レポート生成関数
async def generate_report(report_type: str) -> Dict[str, Any]:
    """指定されたタイプのレポートを生成します"""
    try:
        if report_type not in REPORT_TYPES:
            return {
                "success": False,
                "error": f"不明なレポートタイプ: {report_type}"
            }
        
        # レポートタイプに応じた処理
        if report_type == "usage":
            report_data = await generate_usage_report()
        elif report_type == "performance":
            report_data = await generate_performance_report()
        elif report_type == "error":
            report_data = await generate_error_report()
        elif report_type == "summary":
            report_data = await generate_summary_report()
        else:
            return {
                "success": False,
                "error": f"レポートタイプ {report_type} の生成処理が実装されていません"
            }
        
        return {
            "success": True,
            "report": report_data
        }
    except Exception as e:
        logger.error(f"レポート生成中にエラーが発生しました: {str(e)}")
        return {
            "success": False,
            "error": f"レポート生成エラー: {str(e)}"
        }

# 使用状況レポート生成
async def generate_usage_report() -> Dict[str, Any]:
    """使用状況レポートを生成します"""
    try:
        # 過去7日間のデータを取得
        data = load_execution_data(days=7)
        
        if not data:
            return {
                "type": "text",
                "title": "使用状況レポート",
                "content": "データがありません。GASコードを実行すると、使用状況が記録されます。"
            }
        
        # 日付ごとの実行回数を集計
        daily_counts = {}
        for item in data:
            date = item.get("timestamp", "").split("T")[0]
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        # チャートデータの作成
        chart_data = {
            "type": "bar",
            "labels": list(daily_counts.keys()),
            "values": list(daily_counts.values())
        }
        
        # 実行されたスクリプトのタイトルを集計
        script_titles = {}
        for item in data:
            title = item.get("title", "無題")
            script_titles[title] = script_titles.get(title, 0) + 1
        
        # 表形式のデータを作成
        table_data = [
            {"スクリプト": title, "実行回数": count}
            for title, count in sorted(script_titles.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "type": "chart",
            "title": "過去7日間の使用状況",
            "data": chart_data,
            "table": {
                "headers": ["スクリプト", "実行回数"],
                "data": table_data
            }
        }
    except Exception as e:
        logger.error(f"使用状況レポート生成中にエラーが発生しました: {str(e)}")
        return {
            "type": "text",
            "title": "使用状況レポート",
            "content": f"レポート生成中にエラーが発生しました: {str(e)}"
        }

# パフォーマンスレポート生成
async def generate_performance_report() -> Dict[str, Any]:
    """パフォーマンスレポートを生成します"""
    try:
        # 過去7日間のデータを取得
        data = load_execution_data(days=7)
        
        if not data:
            return {
                "type": "text",
                "title": "パフォーマンスレポート",
                "content": "データがありません。GASコードを実行すると、パフォーマンス情報が記録されます。"
            }
        
        # 実行時間を持つデータのみを抽出
        performance_data = []
        for item in data:
            if "execution_time" in item:
                performance_data.append(item)
        
        if not performance_data:
            return {
                "type": "text",
                "title": "パフォーマンスレポート",
                "content": "実行時間データがありません。"
            }
        
        # スクリプトごとの平均実行時間を計算
        script_performance = {}
        for item in performance_data:
            title = item.get("title", "無題")
            time = item.get("execution_time", 0)
            
            if title not in script_performance:
                script_performance[title] = {"total_time": 0, "count": 0}
            
            script_performance[title]["total_time"] += time
            script_performance[title]["count"] += 1
        
        # 平均実行時間を計算
        for title in script_performance:
            script_performance[title]["avg_time"] = script_performance[title]["total_time"] / script_performance[title]["count"]
        
        # 表形式のデータを作成
        table_data = [
            {
                "スクリプト": title,
                "平均実行時間 (秒)": round(data["avg_time"], 2),
                "実行回数": data["count"]
            }
            for title, data in sorted(script_performance.items(), key=lambda x: x[1]["avg_time"], reverse=True)
        ]
        
        # チャートデータの作成
        chart_data = {
            "type": "bar",
            "labels": [item["スクリプト"] for item in table_data],
            "values": [item["平均実行時間 (秒)"] for item in table_data]
        }
        
        return {
            "type": "chart",
            "title": "スクリプト別平均実行時間",
            "data": chart_data,
            "table": {
                "headers": ["スクリプト", "平均実行時間 (秒)", "実行回数"],
                "data": table_data
            }
        }
    except Exception as e:
        logger.error(f"パフォーマンスレポート生成中にエラーが発生しました: {str(e)}")
        return {
            "type": "text",
            "title": "パフォーマンスレポート",
            "content": f"レポート生成中にエラーが発生しました: {str(e)}"
        }

# エラーレポート生成
async def generate_error_report() -> Dict[str, Any]:
    """エラーレポートを生成します"""
    try:
        # 過去7日間のデータを取得
        data = load_execution_data(days=7)
        
        if not data:
            return {
                "type": "text",
                "title": "エラーレポート",
                "content": "データがありません。GASコードを実行すると、エラー情報が記録されます。"
            }
        
        # エラーを含むデータのみを抽出
        error_data = []
        for item in data:
            if not item.get("success", True) and "error" in item:
                error_data.append(item)
        
        if not error_data:
            return {
                "type": "text",
                "title": "エラーレポート",
                "content": "エラーデータがありません。すべての実行は成功しています。"
            }
        
        # エラータイプごとの発生回数を集計
        error_types = {}
        for item in error_data:
            error_msg = item.get("error", "不明なエラー")
            # エラーメッセージの先頭部分を抽出（長すぎる場合は切り詰める）
            error_type = error_msg.split(":")[0] if ":" in error_msg else error_msg[:50]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        # 表形式のデータを作成
        table_data = [
            {"エラータイプ": error_type, "発生回数": count}
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)
        ]
        
        # チャートデータの作成
        chart_data = {
            "type": "pie",
            "labels": [item["エラータイプ"] for item in table_data],
            "values": [item["発生回数"] for item in table_data]
        }
        
        # 最近のエラー一覧を作成
        recent_errors = []
        for item in sorted(error_data, key=lambda x: x.get("timestamp", ""), reverse=True)[:5]:
            timestamp = item.get("timestamp", "").replace("T", " ").split(".")[0]
            title = item.get("title", "無題")
            error = item.get("error", "不明なエラー")
            recent_errors.append(f"• {timestamp} - {title}: {error}")
        
        recent_errors_text = "\n\n".join(recent_errors)
        
        return {
            "type": "chart",
            "title": "エラータイプ別発生回数",
            "data": chart_data,
            "table": {
                "headers": ["エラータイプ", "発生回数"],
                "data": table_data
            },
            "recent_errors": recent_errors_text
        }
    except Exception as e:
        logger.error(f"エラーレポート生成中にエラーが発生しました: {str(e)}")
        return {
            "type": "text",
            "title": "エラーレポート",
            "content": f"レポート生成中にエラーが発生しました: {str(e)}"
        }

# サマリーレポート生成
async def generate_summary_report() -> Dict[str, Any]:
    """サマリーレポートを生成します"""
    try:
        # 過去7日間のデータを取得
        data = load_execution_data(days=7)
        
        if not data:
            return {
                "type": "text",
                "title": "サマリーレポート",
                "content": "データがありません。GASコードを実行すると、情報が記録されます。"
            }
        
        # 基本的な統計情報を計算
        total_executions = len(data)
        successful_executions = sum(1 for item in data if item.get("success", False))
        error_executions = total_executions - successful_executions
        success_rate = (successful_executions / total_executions) * 100 if total_executions > 0 else 0
        
        # スクリプトの種類数をカウント
        unique_scripts = set(item.get("title", "無題") for item in data)
        
        # 日付ごとの実行回数を集計
        daily_counts = {}
        for item in data:
            date = item.get("timestamp", "").split("T")[0]
            daily_counts[date] = daily_counts.get(date, 0) + 1
        
        # 平均実行回数を計算
        avg_executions_per_day = sum(daily_counts.values()) / len(daily_counts) if daily_counts else 0
        
        # サマリーテキストを作成
        summary_text = f"""📊 *GAS Assistant 使用状況サマリー*

*基本情報:*
• 期間: 過去7日間
• 総実行回数: {total_executions}回
• 成功: {successful_executions}回 ({success_rate:.1f}%)
• エラー: {error_executions}回 ({100-success_rate:.1f}%)
• 実行されたスクリプト種類: {len(unique_scripts)}種類
• 1日あたりの平均実行回数: {avg_executions_per_day:.1f}回

*最も実行されたスクリプト:*
"""
        
        # スクリプトごとの実行回数を集計
        script_counts = {}
        for item in data:
            title = item.get("title", "無題")
            script_counts[title] = script_counts.get(title, 0) + 1
        
        # 上位3つのスクリプトを追加
        top_scripts = sorted(script_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        for i, (title, count) in enumerate(top_scripts):
            summary_text += f"{i+1}. {title}: {count}回\n"
        
        # チャートデータの作成
        chart_data = {
            "type": "bar",
            "labels": list(daily_counts.keys()),
            "values": list(daily_counts.values())
        }
        
        return {
            "type": "text",
            "title": "サマリーレポート",
            "content": summary_text,
            "chart": {
                "type": "bar",
                "title": "過去7日間の使用状況",
                "data": chart_data
            }
        }
    except Exception as e:
        logger.error(f"サマリーレポート生成中にエラーが発生しました: {str(e)}")
        return {
            "type": "text",
            "title": "サマリーレポート",
            "content": f"レポート生成中にエラーが発生しました: {str(e)}"
        }

# 実行データの読み込み
def load_execution_data(days: int = 7) -> List[Dict[str, Any]]:
    """指定された日数分の実行データを読み込みます"""
    try:
        data_dir = get_report_data_path()
        all_data = []
        
        # 過去の日付を計算
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 日付範囲内のファイルを読み込む
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            file_path = os.path.join(data_dir, f"execution_data_{date_str}.json")
            
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    all_data.extend(data)
            
            current_date += timedelta(days=1)
        
        return all_data
    except Exception as e:
        logger.error(f"実行データの読み込み中にエラーが発生しました: {str(e)}")
        return []

# チャート画像の生成
def generate_chart_image(chart_data: Dict[str, Any], title: str) -> Optional[str]:
    """チャートデータから画像を生成し、Base64エンコードした文字列を返します"""
    try:
        chart_type = chart_data.get("type", "bar")
        labels = chart_data.get("labels", [])
        values = chart_data.get("values", [])
        
        if not labels or not values:
            return None
        
        plt.figure(figsize=(10, 6))
        
        if chart_type == "bar":
            plt.bar(labels, values)
            plt.xticks(rotation=45)
        elif chart_type == "pie":
            plt.pie(values, labels=labels, autopct='%1.1f%%')
            plt.axis('equal')
        else:
            plt.plot(labels, values)
            plt.xticks(rotation=45)
        
        plt.title(title)
        plt.tight_layout()
        
        # 画像をバイト列として保存
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        # Base64エンコード
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        plt.close()
        
        return img_str
    except Exception as e:
        logger.error(f"チャート画像生成中にエラーが発生しました: {str(e)}")
        return None

# テスト用コード
if __name__ == "__main__":
    # テスト用のデータを生成
    test_data = {
        "title": "テストスクリプト",
        "success": True,
        "execution_time": 1.5,
        "result": {"message": "テスト成功"}
    }
    
    # データを保存
    save_execution_data(test_data)
    
    # 非同期関数を実行するためのヘルパー
    async def test_reports():
        # 各種レポートを生成
        for report_type in REPORT_TYPES:
            print(f"\n=== {REPORT_TYPES[report_type]['name']} ===")
            report = await generate_report(report_type)
            print(json.dumps(report, ensure_ascii=False, indent=2))
    
    # テスト実行
    asyncio.run(test_reports())