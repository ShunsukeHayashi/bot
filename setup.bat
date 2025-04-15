@echo off
echo テレグラムボット環境セットアップスクリプト
echo ======================================

echo 1. 仮想環境を作成しています...
python -m venv venv
call venv\Scripts\activate

echo 2. 必要なパッケージをインストールしています...
pip install -r examples\gas_assistant\requirements.txt

echo 3. セットアップが完了しました！
echo ボットを起動するには以下のコマンドを実行してください:
echo cd examples\gas_assistant
echo python telegram_gas_agent.py