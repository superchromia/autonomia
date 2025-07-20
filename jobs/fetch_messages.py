import os
from telethon import TelegramClient
from sqlalchemy.ext.asyncio import AsyncSession
from models.message import Message
from repositories.message_repository import MessageRepository
import aiohttp
import shutil
from storage.local import LocalStorageBackend
from storage.s3 import S3StorageBackend
from storage.base import StorageBackend
from sqlalchemy import select, func
import asyncio
import logging
from repositories.event_repository import EventRepository
from dependency import dependency
from repositories.user_repository import UserRepository

logger = logging.getLogger("fetch_messages")

async def fetch_all_messages_job():
    # Проверяем, доступен ли Telegram клиент
    if not dependency.telegram_client:
        logger.warning("Telegram client not available - fetch job skipped")
        return
    
    client = dependency.telegram_client
    logger.info("Fetch job started")
    async for session in dependency.get_session():
        async with session.begin():
            repo = EventRepository(session)
            async for dialog in client.iter_dialogs():
                logger.info(f"Processing channel: id={dialog.id}, title={getattr(dialog, 'title', None)}")
                last_id = await repo.get_last_message_id(dialog.id)
                async for msg in client.iter_messages(entity=dialog, min_id=last_id):
                    await repo.save_event(msg)