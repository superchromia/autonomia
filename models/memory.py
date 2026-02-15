# pylint: disable=not-callable

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.sql import func

from models.base import Base


class Memory(Base):
    __tablename__ = "chat_memories"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    chat_id = Column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_message_id = Column(BigInteger, nullable=True)

    memory_text = Column(Text, nullable=False)
    memory_type = Column(String(30), nullable=False, default="fact")
    importance = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)

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

    __table_args__ = (
        Index("ix_chat_memories_chat_active", "chat_id", "is_active"),
        Index("ix_chat_memories_importance", "chat_id", "importance"),
    )

    def __repr__(self):
        return (
            f"<Memory(id={self.id}, chat_id={self.chat_id}, "
            f"type={self.memory_type}, importance={self.importance})>"
        )
