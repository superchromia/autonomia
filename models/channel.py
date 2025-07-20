from sqlalchemy import Column, BigInteger, String, Text
from models.base import Base

class Channel(Base):
    __tablename__ = 'channels'
    id = Column(BigInteger, primary_key=True)
    title = Column(String, nullable=False)
    username = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    type = Column(String, nullable=True)  # group, channel, supergroup

    def __repr__(self):
        return f"<Channel(id={self.id}, title={self.title})>" 