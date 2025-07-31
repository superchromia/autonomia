from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=True)
    sender_id = Column(BigInteger, nullable=True, index=True)

    # Important metadata
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    message_type = Column(String(50), nullable=False, default="text", index=True)
    is_read = Column(Boolean, default=False, index=True)
    is_deleted = Column(Boolean, default=False)

    # Full data in JSONB
    raw_data = Column(JSONB, nullable=False)  # Full message data

    # System fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    chat = relationship("Chat", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        PrimaryKeyConstraint("message_id", "chat_id"),
        Index("ix_messages_chat_date", "chat_id", "date"),
        Index("ix_messages_sender_date", "sender_id", "date"),
        Index("ix_messages_type_date", "message_type", "date"),
        Index("ix_messages_unread", "chat_id", "is_read"),
    )

    def __repr__(self):
        return f"<Message(message_id={self.message_id}, " f"chat_id={self.chat_id}, sender_id={self.sender_id})>"
