from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from models.base import Base


class User(Base):
    """Model for storing Telegram users"""

    __tablename__ = "users"

    # Main fields for fast search
    id = Column(BigInteger, primary_key=True)

    # Important metadata
    username = Column(String(100), nullable=True, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_scam = Column(Boolean, default=False)
    is_fake = Column(Boolean, default=False)
    is_bot = Column(Boolean, default=False, index=True)
    is_premium = Column(Boolean, default=False)

    # Full data in JSONB
    raw_data = Column(JSONB, nullable=False)  # Full user data

    # System fields
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Indexes for performance
    __table_args__ = (Index("ix_users_username", "username"),)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return f"@{self.username}"
        else:
            return f"User {self.id}"

    @property
    def chat_representation(self):
        if self.username:
            return f"@{self.username}"
        elif self.first_name:
            return f"{self.first_name}"
        elif self.last_name:
            return f"{self.last_name}"
        else:
            return f"User {self.id}"
