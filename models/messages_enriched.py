from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Column, ForeignKey, PrimaryKeyConstraint, String
from sqlalchemy.orm import relationship

from models.base import Base


class EnrichedMessage(Base):
    __tablename__ = "messages_enriched"

    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False)
    message_id = Column(BigInteger, nullable=False)
    context = Column(String, nullable=True)
    meaning = Column(String, nullable=True)
    embeddings = Column(Vector(4096), nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="enriched_messages")

    __table_args__ = (PrimaryKeyConstraint("chat_id", "message_id"),)

    def __repr__(self):
        return f"<EnrichedMessage(chat_id={self.chat_id}, message_id={self.message_id}, context={self.context}, meaning={self.meaning})>"
