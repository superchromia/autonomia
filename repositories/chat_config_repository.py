from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models.chat_config import ChatConfig


class ChatConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(self) -> List[ChatConfig]:
        result = await self.session.execute(select(ChatConfig))
        return result.scalars().all()

    async def get(self, chat_id: int) -> Optional[ChatConfig]:
        result = await self.session.execute(
            select(ChatConfig).where(ChatConfig.chat_id == chat_id)
        )
        return result.scalar_one_or_none()

    async def create_or_update(self, cfg: ChatConfig) -> ChatConfig:
        existing = await self.get(cfg.chat_id)
        if existing:
            existing.save_messages = cfg.save_messages
            existing.load_from_date = cfg.load_from_date
            existing.system_prompt = cfg.system_prompt
            existing.answer_threshold = cfg.answer_threshold
        else:
            self.session.add(cfg)
        await self.session.commit()
        return cfg

    async def delete(self, chat_id: int) -> bool:
        obj = await self.get(chat_id)
        if not obj:
            return False
        await self.session.delete(obj)
        await self.session.commit()
        return True
