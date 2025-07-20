from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Index
from models.base import Base
import datetime

class Message(Base):
    __tablename__ = 'messages'
    __table_args__ = (
        Index('ix_channel_id_date', 'channel_id', 'date'),
    )
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    channel_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    sender_id = Column(BigInteger, nullable=True)
    text = Column(Text, nullable=True)
    date = Column(DateTime, nullable=False)
    image_path = Column(String, nullable=True)

    def __repr__(self):
        return f"<Message(channel_id={self.channel_id}, message_id={self.message_id})>" 