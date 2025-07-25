from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.types import Message as TelegramMessage

from models.message import Message
from models.messages_enriched import EnrichedMessage
from utils import convert_telegram_obj


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def omit_key_fields(dict_obj: dict, keys: list[str]) -> dict:
        return {k: v for k, v in dict_obj.items() if k not in keys}

    @staticmethod
    def prepare_message_obj(message: TelegramMessage) -> dict:
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

        if message.action:
            message_type = "action"

        # Extract sender_id properly
        sender_id = None
        if message.sender_id:
            if hasattr(message.sender_id, "user_id"):
                sender_id = message.sender_id.user_id
            elif hasattr(message.sender_id, "channel_id"):
                sender_id = message.sender_id.channel_id
            elif isinstance(message.sender_id, int):
                sender_id = message.sender_id
            else:
                # If it's an object, try to get the id attribute
                sender_id = getattr(message.sender_id, "id", None)

        chat_id = message.peer_id.channel_id if hasattr(message.peer_id, "channel_id") else message.peer_id.user_id
        return dict(
            message_id=message.id,
            chat_id=chat_id,
            sender_id=sender_id,
            date=message.date,
            message_type=message_type,
            is_read=getattr(message, "read", False),
            raw_data=convert_telegram_obj(message),
        )

    async def save_messages_batch(self, messages: list[TelegramMessage]) -> list[Message]:
        """Save messages batch to database"""
        async with self.session.begin():
            stmt = insert(Message).values([self.prepare_message_obj(msg) for msg in messages]).on_conflict_do_nothing()
            await self.session.execute(stmt)
            return messages

    async def save_message(self, message: TelegramMessage) -> Message:
        message_obj = self.prepare_message_obj(message)
        async with self.session.begin():
            stmt = (
                insert(Message)
                .values([message_obj])
                .on_conflict_do_update(
                    index_elements=("message_id", "chat_id"),
                    set_=self.omit_key_fields(message_obj, ["message_id", "chat_id"]),
                )
            )
            await self.session.execute(stmt)

    async def delete_messages(self, chat_id: int, deleted_ids: list[int]) -> int:
        async with self.session.begin():
            deleted_count = 0
            for message_id in deleted_ids:
                result = await self.session.execute(
                    select(Message).where(
                        Message.message_id == message_id,
                        Message.chat_id == chat_id,
                    )
                )
                message = result.scalar_one_or_none()
                if message:
                    message.is_deleted = True
                    message.updated_at = datetime.now(UTC)
                    deleted_count += 1

            return deleted_count > 0

    async def get_message(self, message_id: int, chat_id: int) -> Message | None:
        async with self.session.begin():
            result = await self.session.execute(
                select(Message).where(
                    Message.message_id == message_id,
                    Message.chat_id == chat_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_first_message_id(self, chat_id: int) -> int:
        async with self.session.begin():
            result = await self.session.execute(select(func.min(Message.message_id)).where(Message.chat_id == chat_id))
            return result.scalar_one() or 0

    async def get_chat_id(self, message_id: int) -> int:
        result = await self.session.execute(select(Message.chat_id).where(Message.message_id == message_id))
        return result.scalar_one()

    async def get_messages_thread(self, chat_id: int, message_id: int) -> list[Message]:
        messages = []
        async with self.session.begin():
            while message_id is not None:
                result = await self.session.execute(
                    select(Message).where(
                        Message.chat_id == chat_id,
                        Message.message_id == message_id,
                    )
                )
                message = result.scalar_one_or_none()
                if message and message.raw_data:
                    messages.append(message)
                    reply_data = message.raw_data.get("reply_to", {})
                    message_id = reply_data.get("reply_to_msg_id") if reply_data else None
                else:
                    message_id = None
        if messages:
            messages.sort(key=lambda x: x.message_id)
            return messages[:-1]
        return messages

    async def get_previous_n_messages(self, chat_id: int, message_id: int, n: int) -> list[Message]:
        messages = []
        async with self.session.begin():
            result = await self.session.execute(
                select(Message).where(
                    Message.chat_id == chat_id,
                    Message.message_id < message_id,
                    Message.message_id >= message_id - n,
                )
            )
            messages = result.scalars().all()
        return messages

    async def get_unenriched_messages(self, chat_id: int, limit: int = 10) -> list[Message]:
        async with self.session.begin():
            # Get messages that don't have enriched versions
            self.session.echo = True
            result = await self.session.execute(
                select(Message.message_id)
                .outerjoin(EnrichedMessage, (Message.message_id == EnrichedMessage.message_id) & (Message.chat_id == EnrichedMessage.chat_id))
                .where(Message.chat_id == chat_id, EnrichedMessage.message_id.is_(None))
                .order_by(Message.message_id.desc())
                .limit(limit)
            )
            return result.scalars().all()
