import asyncio
import logging
from typing import List

from dependency import dependency
from processing.enrich_message import process_message
from repositories.chat_config_repository import ChatConfigRepository
from repositories.enriched_message_repository import EnrichedMessageRepository
from repositories.message_repository import MessageRepository

logger = logging.getLogger("enrich_old_messages")


async def get_unenriched_messages(
    limit: int = 1000,
) -> List[tuple[int, int]]:

    async for session in dependency.get_session():
        chat_config_repo = ChatConfigRepository(session)
        message_repo = MessageRepository(session)

        chat_configs = await chat_config_repo.list_all()
        active_configs = [cfg.chat_id for cfg in chat_configs if cfg.save_messages]
        active_configs = [1501441278]
    unenriched = []
    for chat_id in active_configs:
        msg_ids = await message_repo.get_unenriched_messages(chat_id=chat_id, limit=limit)
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
