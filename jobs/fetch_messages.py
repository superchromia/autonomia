import asyncio
import logging
from collections.abc import AsyncGenerator
from datetime import UTC
from typing import TypeVar

from telethon import TelegramClient, types

from dependency import dependency
from repositories.chat_config_repository import ChatConfigRepository
from repositories.message_repository import MessageRepository

logger = logging.getLogger("fetch_messages")

T = TypeVar("T")


async def messages_generator(
    client: TelegramClient, chat_id: int, offset_id: int
):

    try:
        logger.info(
            f"Fetching messages for chat_id={chat_id}, offset_id={offset_id}"
        )
        stop_fetching = True
        async for msg in client.iter_messages(
            entity=chat_id,
            offset_id=offset_id,
        ):
            offset_id = max(offset_id, msg.id)
            stop_fetching = False
            yield msg

    except Exception as e:
        logger.exception(f"Error fetching messages for chat_id={chat_id}: {e}")
        raise


async def take_batch(
    generator: AsyncGenerator[T, None], batch_size: int = 1000
) -> AsyncGenerator[list[T], None]:
    batch = []
    async for item in generator:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


async def fetch_all_messages_job():
    # Check if Telegram client is available
    if not dependency.telegram_client:
        logger.warning("Telegram client not available - fetch job skipped")
        return

    client = dependency.telegram_client
    logger.info("Fetch job started")

    async for session in dependency.get_session():
        # Get repositories
        chat_config_repo = ChatConfigRepository(session)
        message_repo = MessageRepository(session)

        # Get all chat configurations where save_messages=True
        chat_configs = await chat_config_repo.list_all()
        active_configs = {
            cfg.chat_id: cfg for cfg in chat_configs if cfg.save_messages
        }

        if not active_configs:
            logger.info("No active chat configs found - nothing to fetch")
            return

        # Process each active chat
        async for dialog in client.iter_dialogs():
            dialog: types.Dialog
            chat_id = dialog.entity.id
            if chat_id not in active_configs:
                continue
            offset_id = await message_repo.get_first_message_id(chat_id)
            messages_gen = messages_generator(client, chat_id, offset_id)
            async for batch in take_batch(messages_gen):
                await message_repo.save_messages_batch(batch)
                logger.info(f"Saved messages batch: {len(batch)}")
