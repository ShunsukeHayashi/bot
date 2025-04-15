# Bot Project

This is a bot project that integrates with various services.

## Features

- Line Bot Integration
- Agent Manager
- Intent Analysis
- Supabase Database Integration
- Devin API Integration
- Telegram GAS Assistant Integration

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure environment variables in `.env` (see `.env.example` for required variables)
4. Run the application: `python app/main.py`

## Project Structure

- `app/` - Main application code
  - `agent/` - Agent management and intent analysis
  - `database/` - Database integration
  - `devin_integration/` - Devin API integration
  - `line_bot/` - Line bot implementation
  - `main.py` - Application entry point
- `examples/` - Example implementations
  - `gas_assistant/` - Telegram GAS Assistant example
- `test/` - Test files

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request
