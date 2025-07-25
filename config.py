from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration using Pydantic for validation"""

    # Admin credentials
    admin_username: str = Field(
        default="admin",
        env="ADMIN_USERNAME",
        description="Admin panel username",
    )
    admin_password: str = Field(
        default="admin123",
        env="ADMIN_PASSWORD",
        description="Admin panel password",
    )

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost/superchromia",
        env="DATABASE_URL",
        description="Database connection URL",
    )

    # Telegram
    telegram_api_id: str | None = Field(
        default=None, env="TELEGRAM_API_ID", description="Telegram API ID"
    )
    telegram_api_hash: str | None = Field(
        default=None, env="TELEGRAM_API_HASH", description="Telegram API Hash"
    )
    telethon_session_string: str = Field(
        env="TELETHON_SESSION_STRING",
        description="Telegram session ",
    )

    # Security
    secret_key: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY",
        description="Secret key for session encryption",
    )

    # Validation
    @field_validator("admin_username")
    @classmethod
    def validate_admin_username(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Admin username cannot be empty")
        if len(v) < 3:
            raise ValueError("Admin username must be at least 3 characters")
        return v.strip()

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Admin password cannot be empty")
        if len(v) < 6:
            raise ValueError("Admin password must be at least 6 characters")
        return v

    @field_validator("telegram_api_id")
    @classmethod
    def validate_telegram_api_id(cls, v):
        if v is not None:
            try:
                int(v)
            except ValueError as err:
                raise ValueError(
                    "TELEGRAM_API_ID must be a valid integer"
                ) from err
        return v

    @field_validator("telegram_api_hash")
    @classmethod
    def validate_telegram_api_hash(cls, v):
        if v is not None and len(v) != 32:
            raise ValueError("TELEGRAM_API_HASH must be exactly 32 characters")
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    def validate_required_telegram_config(self) -> None:
        """Validate that required Telegram configuration is present"""
        if not self.telegram_api_id:
            raise ValueError(
                "TELEGRAM_API_ID environment variable is required"
            )
        if not self.telegram_api_hash:
            raise ValueError(
                "TELEGRAM_API_HASH environment variable is required"
            )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


# Create global config instance
config = Config()
