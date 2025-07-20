import logging

from dependency import dependency
from repositories.event_repository import EventRepository

logger = logging.getLogger("fetch_messages")


async def fetch_all_messages_job():
    # Check if Telegram client is available
    if not dependency.telegram_client:
        logger.warning("Telegram client not available - fetch job skipped")
        return

    client = dependency.telegram_client
    logger.info("Fetch job started")
    async for session in dependency.get_session():
        async with session.begin():
            repo = EventRepository(session)
            async for dialog in client.iter_dialogs():
                logger.info(f"Processing channel: id={dialog.id}, title={dialog.title}")
                last_id = await repo.get_last_message_id(dialog.id)
                async for msg in client.iter_messages(entity=dialog, min_id=last_id):
                    await repo.save_event(msg)
