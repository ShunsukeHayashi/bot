
cat > telegram_update.json << 'EOJ'
{
  "update_id": 123456789,
  "message": {
    "message_id": 123,
    "from": {
      "id": 987654321,
      "is_bot": false,
      "first_name": "Test",
      "last_name": "User",
      "username": "testuser",
      "language_code": "en"
    },
    "chat": {
      "id": 987654321,
      "first_name": "Test",
      "last_name": "User",
      "username": "testuser",
      "type": "private"
    },
    "date": 1617123456,
    "text": "Hello, bot!"
  }
}
EOJ

TOKEN=$TELEGRAM_TOKEN

curl -X POST \
  -H "Content-Type: application/json" \
  -d @telegram_update.json \
  http://localhost:3001/webhook/$TOKEN

echo ""
