
cat > test_agent_request.json << 'EOJ'
{
  "message": "こんにちは、今日の天気はどうですか？",
  "user_id": "test_user_123",
  "conversation_state": {}
}
EOJ

curl -X POST \
  -H "Content-Type: application/json" \
  -d @test_agent_request.json \
  http://localhost:8000/api/agent/message

echo ""
