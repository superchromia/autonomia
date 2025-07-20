# Autonomia Telegram Bot

Telegram bot for LLM-based processing, analyzing and answering messages using FastAPI and PostgreSQL.

## Features

- **Telegram Integration**: Real-time message processing using Telethon
- **LLM Processing**: Integration with Nebius AI Studio for intelligent responses
- **Database Storage**: PostgreSQL with Alembic migrations for data persistence
- **Cloud Ready**: Optimized for deployment on Render with automatic database creation
- **Health Monitoring**: Built-in health check endpoints

## Quick Start

### Using Dev Containers (Recommended)

1. **Open in Dev Container**
   - Use VS Code with Dev Containers extension
   - The project includes `.devcontainer` configuration

2. **Start the Application**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 5000 --reload
   ```

### Local Development

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   Create a `.env` file:
   ```env
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/telegram
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELETHON_SESSION=autonomia
   NEBIUS_STUDIO_API_KEY=your_nebius_key
   ```

3. **Run the Application**
   ```bash
   uvicorn app:app --host 0.0.0.0 --port 5000 --reload
   ```

**Note:** The application will automatically create the database if it doesn't exist during startup.

## Deployment on Render

### Automatic Deployment

1. **Connect Repository**
   - Go to [render.com](https://render.com)
   - Create a new Web Service
   - Connect your GitHub repository

2. **Configure Environment Variables**
   ```env
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELETHON_SESSION=autonomia
   TELETHON_SESSION_STRING=your_string_session
   NEBIUS_STUDIO_API_KEY=your_nebius_key
   ```

3. **Service Settings**
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path:** `/api/v1/health`

### Database Setup

The PostgreSQL database is automatically created and configured through Render's database service.

### StringSession Setup for Telegram

For cloud deployment, you need to use StringSession instead of session files:

1. **Create StringSession**
   ```bash
   python convert_session.py
   ```

2. **Follow the prompts** to authenticate with Telegram

3. **Add the generated string** to `TELETHON_SESSION_STRING` environment variable in Render

## API Endpoints

- `GET /api/v1/health` - Service health check
- Additional endpoints for message processing and analysis

## Project Structure

```
├── alembic/              # Database migrations
├── api/                  # API endpoints
│   └── v1/              # Version 1 API
├── jobs/                 # Background tasks
├── models/               # SQLAlchemy models
├── repositories/         # Database repositories
├── storage/              # File storage (S3 support)
├── external/             # External service integrations
├── app.py               # Main application
├── dependency.py        # Dependency injection
├── render.yaml          # Render configuration
└── requirements.txt     # Python dependencies
```

## Key Components

### Models
- `Event` - Telegram message events
- `ChatConfig` - Chat configuration settings

### Services
- **Telegram Client** - Handles Telegram API communication
- **Nebius AI** - LLM processing for message analysis
- **Database** - PostgreSQL with automatic migration support

### Features
- **Automatic Database Creation** - Creates database if it doesn't exist
- **StringSession Support** - Secure session management for cloud
- **Health Monitoring** - Built-in health checks
- **Background Jobs** - Automated message processing

## Development

### Prerequisites
- Python 3.11+
- PostgreSQL
- Telegram API credentials
- Nebius AI Studio API key

### Environment Setup
The project uses environment variables for configuration. See the `.env` example above for required variables.

### Database Migrations
Migrations are handled automatically by Alembic during application startup.

## Render Features

- Application automatically adapts to the `$PORT` variable
- Health check endpoint for monitoring
- Secure Telegram client initialization
- Optimized Dockerfile for production
- Automatic database creation if it doesn't exist