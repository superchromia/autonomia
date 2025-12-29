from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base import Base


class ChatConfig(Base):
    __tablename__ = "chat_configs"
    chat_id = Column(
        BigInteger,
        ForeignKey("chats.id", ondelete="CASCADE"),
        primary_key=True,
    )
    save_messages = Column(Boolean, nullable=False, default=True)
    load_from_date = Column(DateTime, nullable=True)
    system_prompt = Column(String, nullable=True)
    answer_threshold = Column(Float, nullable=True)
    enrich_messages = Column(Boolean, nullable=False, default=True)
    recognize_photo = Column(Boolean, nullable=False, default=True)
    response_triggers = Column(
        JSONB,
        nullable=True,
        default=lambda: {
            "on_every_message": False,
            "on_mention": True,
            "on_reply_to_bot": True,
        },
    )
    # Nebius AI model configuration
    text_model = Column(String, nullable=True, default="openai/gpt-oss-120b")
    embeddings_model = Column(String, nullable=True, default="Qwen/Qwen3-Embedding-8B")
    image_model = Column(String, nullable=True, default=None)

    # Relationships
    chat = relationship("Chat", back_populates="config")

    def __repr__(self):
        return (
            f"<ChatConfig(chat_id={self.chat_id}, "
            f"save_messages={self.save_messages}, "
            f"enrich_messages={self.enrich_messages}, "
            f"recognize_photo={self.recognize_photo})>"
        )
