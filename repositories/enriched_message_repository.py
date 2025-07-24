from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.messages_enriched import EnrichedMessage


class EnrichedMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save(self, data: dict) -> EnrichedMessage:
        """Save enriched message data"""
        async with self.session.begin():
            stmt = (
                insert(EnrichedMessage)
                .values(data)
                .on_conflict_do_update(
                    index_elements=("chat_id", "message_id"),
                    set_={
                        "context": data["context"],
                        "meaning": data["meaning"],
                        "embeddings": data["embeddings"],
                    },
                )
            )
            await self.session.execute(stmt)
            return data

    async def get_one(self, chat_id: int, message_id: int) -> EnrichedMessage | None:
        """Get one enriched message by chat_id and message_id"""
        async with self.session.begin():
            result = await self.session.execute(
                select(EnrichedMessage).where(
                    EnrichedMessage.chat_id == chat_id,
                    EnrichedMessage.message_id == message_id,
                )
            )
            return result.scalar_one_or_none()

    async def get_all(self) -> list[EnrichedMessage]:
        """Get all enriched messages"""
        async with self.session.begin():
            result = await self.session.execute(select(EnrichedMessage))
            return result.scalars().all()
