from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base import Base


class Event(Base):
    __tablename__ = "events"

    event_id = Column(BigInteger, nullable=False, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_json = Column(JSONB, nullable=False)

    # Relationships
    chat = relationship("Chat")

    __table_args__ = (
        Index("ix_events_chat_id", "chat_id"),
        Index("ix_events_message_id", "message_id"),
    )

    __table_args__ = (
        Index("ix_events_chat_id", "chat_id"),
        Index("ix_events_message_id", "message_id"),
    )
