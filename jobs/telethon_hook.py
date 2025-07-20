import logging

from telethon import events

from dependency import dependency
from repositories.event_repository import EventRepository

logger = logging.getLogger("telethon_hook")

tg = dependency.telegram_client


@tg.on(events.NewMessage)
async def handler(event):
    async for session in dependency.get_session():
        async with session.begin():
            event_repo = EventRepository(session)
            try:
                logger.info(f"Received: {event}")
                await event_repo.save_event(event)
                await event.message.mark_read()
            except Exception as e:
                logger.exception(f"Failed to save event: {e}")
