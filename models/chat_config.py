from sqlalchemy import BigInteger, Boolean, Column, ForeignKey
from sqlalchemy.orm import relationship

from models.base import Base


class ChatConfig(Base):
    __tablename__ = "chat_configs"
    chat_id = Column(BigInteger, ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    enrich_messages = Column(Boolean, nullable=False, default=True)
    recognize_photo = Column(Boolean, nullable=False, default=True)

    # Relationships
    chat = relationship("Chat", back_populates="config")

    def __repr__(self):
        return f"<ChatConfig(chat_id={self.chat_id}, " f"enrich_messages={self.enrich_messages}, " f"recognize_photo={self.recognize_photo})>"
