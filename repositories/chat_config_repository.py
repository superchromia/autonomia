from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models.chat_config import ChatConfig
from datetime import datetime

class ChatConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def upsert_chat_config(self, chat_id: int, save_messages: bool = True, load_from_date: datetime = None, system_prompt: str = None, answer_threshold: float = None):
        result = await self.session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
        config = result.scalar_one_or_none()
        if config:
            config.save_messages = save_messages
            config.load_from_date = load_from_date
            config.system_prompt = system_prompt
            config.answer_threshold = answer_threshold
        else:
            config = ChatConfig(chat_id=chat_id, save_messages=save_messages, load_from_date=load_from_date, system_prompt=system_prompt, answer_threshold=answer_threshold)
            self.session.add(config)
        await self.session.commit()
        return config

    async def get_chat_config(self, chat_id: int):
        result = await self.session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
        return result.scalar_one_or_none() 