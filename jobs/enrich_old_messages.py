import asyncio
import logging
from typing import List

from sqlalchemy.future import select

from dependency import dependency
from models.chat_config import ChatConfig
from models.message import Message
from processing.enrich_message import process_message

logger = logging.getLogger("enrich_old_messages")


async def get_unenriched_messages(
    limit: int = 1000,
) -> List[tuple[int, int]]:

    async for session in dependency.get_session():
        # Get chat configs with enrich_messages enabled
        result = await session.execute(select(ChatConfig))
        chat_configs = result.scalars().all()
        active_configs = [cfg.chat_id for cfg in chat_configs if cfg.enrich_messages]

        unenriched = []
        for chat_id in active_configs:
            # Get unenriched messages for this chat
            result = await session.execute(select(Message.message_id).where(Message.chat_id == chat_id).limit(limit))
            msg_ids = result.scalars().all()
            for msg_id in msg_ids:
                unenriched.append((chat_id, msg_id))
        return unenriched


async def enrich_old_messages_job(limit: int = 100):
    """Main job to enrich old messages"""
    logger.info(f"Starting enrichment job for {limit} messages")

    async for session in dependency.get_session():
        try:
            unenriched_messages = await get_unenriched_messages(limit)

            for chat_id, msg_id in unenriched_messages:
                await process_message(session, chat_id, msg_id)

        except Exception as e:
            logger.exception(f"Error in enrichment job: {e}")
            raise


async def main():
    """Main function to run the enrichment job"""
    await enrich_old_messages_job(limit=100)
    logger.info("Enrichment job completed")


if __name__ == "__main__":
    asyncio.run(main())
