from sqlalchemy import BigInteger, Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.base import Base


class Media(Base):
    """Model for storing media file references"""

    __tablename__ = "media"

    # Primary key - file reference as base64 string
    file_reference = Column(String, primary_key=True)

    # Foreign key to chat
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False, index=True)

    # Foreign key to message
    message_id = Column(BigInteger, ForeignKey("messages.message_id"), nullable=False, index=True)

    # Media type (photo, video, document, etc.)
    media_type = Column(String(50), nullable=False, index=True)

    # Text description of the media
    text_description = Column(Text, nullable=True)

    # Relationships
    chat = relationship("Chat", back_populates="media")

    # System fields
    created_at = Column(BigInteger, server_default=func.extract("epoch", func.now()) * 1000, nullable=False)
    updated_at = Column(BigInteger, server_default=func.extract("epoch", func.now()) * 1000, onupdate=func.extract("epoch", func.now()) * 1000, nullable=False)

    def __repr__(self):
        return (
            f"<Media(file_reference='{self.file_reference[:20]}...', "
            f"media_type='{self.media_type}', "
            f"description='{self.text_description[:50] if self.text_description else None}...')>"
        )
