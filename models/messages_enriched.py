from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, Column, PrimaryKeyConstraint, String

from models.base import Base


class EnrichedMessage(Base):
    __tablename__ = "messages_enriched"

    chat_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    context = Column(String, nullable=True)
    meaning = Column(String, nullable=True)
    embeddings = Column(Vector(4096), nullable=True)

    __table_args__ = (PrimaryKeyConstraint("chat_id", "message_id"),)

    def __repr__(self):
        return f"<EnrichedMessage(chat_id={self.chat_id}, message_id={self.message_id}, context={self.context}, meaning={self.meaning})>"
