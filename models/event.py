from sqlalchemy import JSON, BigInteger, Column, DateTime, PrimaryKeyConstraint

from models.base import Base


class Event(Base):
    __tablename__ = "events"
    chat_id = Column(BigInteger, nullable=False)
    message_id =  Column(BigInteger, nullable=False)
    utc_dttm = Column(DateTime, nullable=False)
    sender_id = Column(BigInteger, nullable=False)
    event_json = Column(JSON, nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("chat_id", "message_id"),
    )
