from sqlalchemy import Column, BigInteger, String
from models.base import Base

class UserContext(Base):
    __tablename__ = 'user_contexts'
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    alias = Column(String, nullable=True)
    role = Column(String, nullable=True)

    def __repr__(self):
        return f"<UserContext(id={self.id}, username={self.username}, alias={self.alias}, role={self.role})>" 