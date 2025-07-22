from sqlalchemy import BigInteger, Column, DateTime, Index, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import Base


class Event(Base):
    __tablename__ = "events"

    event_id = Column(
        BigInteger, nullable=False, primary_key=True, autoincrement=True
    )
    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    event_json = Column(JSONB, nullable=False)

    __table_args__ = (
        Index("ix_events_chat_id", "chat_id"),
        Index("ix_events_message_id", "message_id"),
    )

    __table_args__ = (
        Index("ix_events_chat_id", "chat_id"),
        Index("ix_events_message_id", "message_id"),
    )
