from datetime import datetime, timezone, timedelta
import logging
from telethon import events
from dependency import dependency
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository
from repositories.channel_repository import ChannelRepository
from models.message import Message
from api.v1.utils import get_nebius_client
from external.nebius import NebiusAIStudioClient
from telethon.tl.types import MessageEntityMention, MessageEntityMentionName
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import SendMessageTypingAction
from repositories.event_repository import EventRepository

logger = logging.getLogger("telethon_hook")

# Проверяем, доступен ли Telegram клиент
if dependency.telegram_client:
    tg_client = dependency.telegram_client

    @tg_client.on(events.NewMessage)
    async def handler(event):
        async for session in dependency.get_session():
            async with session.begin():
                event_repo = EventRepository(session)
                try:
                    logger.info(f'Received: {event}')
                    await event_repo.save_event(event)
                except Exception as e:
                    logger.exception(f"Failed to save event: {e}")
else:
    logger.warning("Telegram client not available - telethon hooks disabled")
