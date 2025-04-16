# AI Agent LINE Bot & Telegram Bot

This repository contains a LINE bot and Telegram bot implementation with enhanced AI agent capabilities, conversation state management, user intent analysis, and Google Apps Script (GAS) integration.

## Features

- LINE Messaging API integration (V3 SDK)
- Telegram Bot API integration
- Supabase backend for database storage
- Conversation state management for contextual interactions
- User intent analysis for better understanding of requests
- Dynamic response generation based on user interactions
- Devin API integrations as tool calls within chat threads
- Google Apps Script (GAS) integration for JavaScript code execution
- Feedback loop to improve responses

## Project Structure

```
.
├── app/
│   ├── agent/          # AI agent implementation
│   ├── database/       # Supabase client and database operations
│   ├── devin_integration/ # Devin API integrations
│   ├── gas_integration/ # GAS interpreter integration
│   ├── line_bot/       # LINE bot implementation
│   ├── protocols/      # Protocol definitions
│   ├── telegram_bot/   # Telegram bot implementation
│   ├── utils/          # Utility functions
│   └── main.py         # FastAPI application
├── examples/
│   └── gas_assistant/  # GAS integration examples
├── requirements.txt    # Python dependencies
├── Procfile           # Process file for deployment
└── runtime.txt        # Python runtime specification
```

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up environment variables (see `.env.example`)
4. Run the application: `uvicorn app.main:app --reload`

## Deployment

Details for deployment will be provided in a separate document.
