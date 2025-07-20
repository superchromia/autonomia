import logging
from datetime import datetime, timedelta, timezone

from telethon import events
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import (
    MessageEntityMention,
    MessageEntityMentionName,
    SendMessageTypingAction,
)

from dependency import dependency
from repositories.event_repository import EventRepository

logger = logging.getLogger("telethon_hook")

# Check if Telegram client is available
if dependency.telegram_client:
    tg_client = dependency.telegram_client

    @tg_client.on(events.NewMessage)
    async def handler(event):
        async for session in dependency.get_session():
            async with session.begin():
                event_repo = EventRepository(session)
                try:
                    logger.info(f"Received: {event}")
                    await event_repo.save_event(event)
                except Exception as e:
                    logger.exception(f"Failed to save event: {e}")

else:
    logger.warning("Telegram client not available - telethon hooks disabled")
