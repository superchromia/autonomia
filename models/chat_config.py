from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from models.base import Base


class ChatConfig(Base):
    __tablename__ = "chat_configs"
    chat_id = Column(BigInteger, ForeignKey("chats.id"), primary_key=True)
    save_messages = Column(Boolean, nullable=False, default=True)
    enrich_messages = Column(Boolean, nullable=False, default=True)
    recognize_photo = Column(Boolean, nullable=False, default=True)
    load_from_date = Column(DateTime, nullable=True)
    system_prompt = Column(String, nullable=True)
    answer_threshold = Column(Float, nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="config")

    def __repr__(self):
        return (
            f"<ChatConfig(chat_id={self.chat_id}, save_messages={self.save_messages}, "
            f"enrich_messages={self.enrich_messages}, recognize_photo={self.recognize_photo}, "
            f"load_from_date={self.load_from_date}, system_prompt={self.system_prompt}, "
            f"answer_threshold={self.answer_threshold})>"
        )
