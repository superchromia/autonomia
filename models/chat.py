from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from models.base import Base


class Chat(Base):
    """Model for storing Telegram chats/channels"""

    __tablename__ = "chats"

    # Main fields for fast search
    id = Column(BigInteger, primary_key=True)
    chat_type = Column(
        String(20), nullable=False, index=True
    )  # user, chat, channel, supergroup

    title = Column(String(255), nullable=True, index=True)
    username = Column(String(100), nullable=True, index=True)
    is_verified = Column(Boolean, default=False)
    is_scam = Column(Boolean, default=False)
    is_fake = Column(Boolean, default=False)
    member_count = Column(Integer, nullable=True)

    raw_data = Column(JSONB, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_chats_type_verified", "chat_type", "is_verified"),
        Index("ix_chats_username", "username"),
        Index("ix_chats_title", "title"),
    )

    def __repr__(self):
        return (
            f"<Chat(id={self.id}, title='{self.title}', "
            f"type='{self.chat_type}')>"
        )
