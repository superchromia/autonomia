from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"

    id = Column(String(120), primary_key=True, nullable=False)
    chat_id = Column(
        BigInteger,
        ForeignKey("chats.id"),
        nullable=False,
        index=True,
    )
    query = Column(Text, nullable=False)
    cron_expression = Column(String(120), nullable=True)
    run_at = Column(DateTime(timezone=True), nullable=True)
    send_to_chat = Column(Boolean, nullable=False, default=True)
    planned_sender_id = Column(BigInteger, nullable=True, index=True)
    reply_to_message_id = Column(BigInteger, nullable=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now,  # type: ignore[arg-type]
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now,  # type: ignore[arg-type]
        onupdate=func.now,  # type: ignore[arg-type]
        nullable=False,
    )

    chat = relationship("Chat")

    __table_args__ = (
        CheckConstraint(
            "(cron_expression IS NOT NULL) <> (run_at IS NOT NULL)",
            name="ck_scheduled_tasks_trigger_mode",
        ),
        Index("ix_scheduled_tasks_run_at", "run_at"),
    )
