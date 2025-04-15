# テレグラムGASアシスタントボット

このリポジトリには、Google Apps Script（GAS）を使用してタスクを実行するためのテレグラムボットが含まれています。

## 機能

- 自然言語でGASコードを生成
- 生成したコードをGoogle Apps Scriptで実行
- 実行結果の表示と分析
- レポート生成機能

## セットアップ手順

### 前提条件

- Python 3.8以上
- Google Apps Scriptのデプロイ済みWebアプリケーション
- Telegramボットトークン

### インストール

1. セットアップスクリプトを実行します：

```bash
setup.bat
```

または手動でセットアップする場合：

```bash
# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
# Windowsの場合
venv\Scripts\activate
# macOS/Linuxの場合
# source venv/bin/activate

# 必要なパッケージをインストール
pip install -r examples/gas_assistant/requirements.txt
```

2. 環境変数を設定します：

`.env`ファイルに以下の環境変数が設定されていることを確認してください：

```
# OpenAI API設定
OPENAI_API_KEY=your_openai_api_key

# Google Apps Script API設定
GAS_API_ENDPOINT=your_gas_web_app_url
GAS_API_KEY=your_gas_api_key

# Telegram Bot設定
TELEGRAM_TOKEN=your_telegram_bot_token
```

## 使用方法

### ボットの起動

```bash
cd examples/gas_assistant
python telegram_gas_agent.py
```

### ボットとの対話

1. Telegramアプリでボットを検索します
2. `/start`コマンドを送信してボットを開始します
3. GASで実行したいタスクを自然言語で説明します
4. ボットがGASコードを生成し、実行オプションを提供します

### 利用可能なコマンド

- `/start` - ボットを開始
- `/help` - ヘルプを表示
- `/cancel` - 現在の操作をキャンセル
- `/settings` - 設定を表示
- `/report` - レポートを表示

## ファイル構成

- `examples/gas_assistant/telegram_gas_agent.py` - メインのテレグラムボットスクリプト
- `examples/gas_assistant/telegram_integration.py` - テレグラム統合モジュール
- `examples/gas_assistant/gas_assistant.py` - GASアシスタントコア機能
- `examples/gas_assistant/gas_report_generator.py` - レポート生成機能
- `examples/gas_assistant/requirements.txt` - 必要なPythonパッケージ

## トラブルシューティング

### ボットが応答しない場合

1. 環境変数が正しく設定されているか確認してください
2. ログを確認して、エラーメッセージを確認してください
3. Telegramボットトークンが有効であることを確認してください

### GASコードの実行エラー

1. GAS APIエンドポイントが正しく設定されているか確認してください
2. GAS APIキーが正しいか確認してください
3. GASウェブアプリケーションが正しくデプロイされているか確認してください
