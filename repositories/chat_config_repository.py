from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.chat_config import ChatConfig


class ChatConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_chat_config(self, chat_id: int):
        result = await self.session.execute(
            select(ChatConfig).where(ChatConfig.chat_id == chat_id)
        )
        return result.scalar_one_or_none()
