from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telethon.tl.types import Channel, Chat, User

from models.chat import Chat as ChatModel
from utils import convert_telegram_obj


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_chat(self, chat: Any) -> ChatModel:
        if isinstance(chat, User):
            chat_type = "user"
            title = f"{chat.first_name} {chat.last_name}"
            username = chat.username
        elif isinstance(chat, Channel):
            chat_type = (
                "supergroup"
                if getattr(chat, "megagroup", False)
                else "channel"
            )
            title = getattr(chat, "title", None)
            username = getattr(chat, "username", None)
        elif isinstance(chat, Chat):
            chat_type = "chat"
            title = getattr(chat, "title", None)
            username = None
        else:
            chat_type = "unknown"
            title = getattr(chat, "title", None)
            username = getattr(chat, "username", None)

        chat_obj = ChatModel(
            id=chat.id,
            chat_type=chat_type,
            title=title,
            username=username,
            is_verified=getattr(chat, "verified", False),
            is_scam=getattr(chat, "scam", False),
            is_fake=getattr(chat, "fake", False),
            member_count=getattr(chat, "participants_count", None),
            raw_data=convert_telegram_obj(chat),
        )

        await self.session.merge(chat_obj)
        return chat_obj

    async def list_all(self) -> list[ChatModel]:
        """Get all chats from database"""
        result = await self.session.execute(
            select(ChatModel).order_by(ChatModel.title)
        )
        return result.scalars().all()

    async def get_by_id(self, chat_id: int) -> ChatModel | None:
        """Get chat by ID"""
        result = await self.session.execute(
            select(ChatModel).where(ChatModel.id == chat_id)
        )
        return result.scalar_one_or_none()
