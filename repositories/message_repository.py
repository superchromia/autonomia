from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.types import Message as TelegramMessage

from models.message import Message
from utils import convert_telegram_obj


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_message(self, message: TelegramMessage) -> Message:
        """Save message to database"""
        # Determine message type
        message_type = "text"
        if hasattr(message, "media") and message.media:
            if hasattr(message.media, "photo"):
                message_type = "photo"
            elif hasattr(message.media, "document"):
                message_type = "document"
            elif hasattr(message.media, "video"):
                message_type = "video"
            elif hasattr(message.media, "audio"):
                message_type = "audio"
            elif hasattr(message.media, "voice"):
                message_type = "voice"
            elif hasattr(message.media, "sticker"):
                message_type = "sticker"
            else:
                message_type = "media"

        message_obj = Message(
            message_id=message.id,
            chat_id=(
                message.peer_id.channel_id
                if hasattr(message.peer_id, "channel_id")
                else message.peer_id.user_id
            ),
            sender_id=(
                message.sender_id.user_id
                if hasattr(message.sender_id, "user_id")
                else message.sender_id
            ),
            date=message.date,
            message_type=message_type,
            is_read=getattr(message, "read", False),
            raw_data=convert_telegram_obj(message),
        )

        await self.session.merge(message_obj)
        return message_obj

    async def create_message(self, message: Message):
        await self.save_message(message)

    async def update_message(self, message: Message):
        await self.save_message(message)

    async def delete_messages(
        self, chat_id: int, deleted_ids: list[int]
    ) -> int:

        deleted_count = 0
        for message_id in deleted_ids:
            message = await self.get_message(
                message_id=message_id, chat_id=chat_id
            )
            if message:
                message.is_deleted = True
                message.updated_at = datetime.now(UTC)
                deleted_count += 1

        return deleted_count > 0

    async def get_message(
        self, message_id: int, chat_id: int
    ) -> Message | None:
        result = await self.session.execute(
            select(Message).where(
                Message.message_id == message_id,
                Message.chat_id == chat_id,
            )
        )
        return result.scalar_one_or_none()
