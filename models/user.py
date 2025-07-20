from sqlalchemy import Column, BigInteger, String
from models.base import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username})>" 