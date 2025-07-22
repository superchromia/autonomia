# Admin Authentication Setup

The admin panel now requires authentication. Here's how to set it up:

## Configuration

The application uses Pydantic for configuration validation. You can configure it using environment variables or a `.env` file.

### Environment Variables

Set the following environment variables to configure admin authentication:

```bash
# Admin credentials (change these in production!)
export ADMIN_USERNAME="your_admin_username"
export ADMIN_PASSWORD="your_secure_password"

# Security key for sessions (change this in production!)
export SECRET_KEY="your-secret-key-change-this-in-production-make-it-at-least-32-chars"
```

### .env File

Create a `.env` file in the project root:

```env
# Admin Panel Configuration
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:password@localhost/superchromia

# Telegram Configuration
TELEGRAM_API_ID=your_telegram_api_id_here
TELEGRAM_API_HASH=your_telegram_api_hash_here
TELEGRAM_SESSION_NAME=superchromia_session

# Security Configuration
SECRET_KEY=your-secret-key-change-this-in-production-make-it-at-least-32-chars
```

## Default Credentials

If no environment variables are set, the system will use these defaults:
- **Username**: `admin`
- **Password**: `admin123`
- **Secret Key**: `your-secret-key-change-this-in-production`

## Configuration Validation

The application validates configuration using Pydantic:

- **Admin Username**: Must be at least 3 characters
- **Admin Password**: Must be at least 6 characters  
- **Telegram API ID**: Must be a valid integer
- **Telegram API Hash**: Must be exactly 32 characters
- **Secret Key**: Must be at least 32 characters long

⚠️ **Warning**: These defaults should be changed in production!

## Accessing the Admin Panel

1. Start your application
2. Navigate to `/admin` in your browser
3. Enter your username and password
4. You'll be redirected to the admin dashboard

## Security Recommendations

1. **Use strong passwords** - Avoid default credentials in production
2. **Use environment variables** - Don't hardcode credentials
3. **Use a strong secret key** - Generate a random secret key for sessions
4. **Use HTTPS** - Always use HTTPS in production
5. **Regular password rotation** - Change passwords periodically

## Example Production Setup

```bash
# Generate a secure secret key
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Set secure admin credentials
export ADMIN_USERNAME="superchromia_admin"
export ADMIN_PASSWORD="your-very-secure-password-here"

# Start the application
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

## Available Admin Views

- **Chats**: View and manage Telegram chats/channels
- **Users**: View and manage Telegram users
- **Chat Configurations**: Configure chat settings and message saving 