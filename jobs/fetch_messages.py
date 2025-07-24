import logging
import asyncio
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
    client: TelegramClient, chat_id: int, load_from_date=None
):
    """Message generator for a specific chat"""
    logger.info(f"Starting to fetch messages for chat_id={chat_id}")

    try:
        # Get all messages from chat with optimized parameters
        # reverse=True - load messages in chronological order
        # limit=None - load all messages (no limit)
        # offset_date=load_from_date - if date is specified, start from it
        # wait_time=0 - don't wait between requests
        # total_count_limit=None - no limit on total count

        offset_id = 0
        while True:
            logger.info(f"Fetching messages for chat_id={chat_id}, offset_id={offset_id}")
            stop_fetching = True
            async for msg in client.iter_messages(
                entity=chat_id,
                reverse=True,
                limit=None,
                offset_id=offset_id,
            ):
                if msg.action:
                    logger.info(
                        f"MessageService action: {msg.action}, skipping it"
                    )
                    continue
                # If start date is specified, skip old messages

                if load_from_date and msg.date < load_from_date.replace(
                    tzinfo=UTC
                ):
                    continue

                offset_id = max(offset_id, msg.id)
                stop_fetching = False
                yield msg
            if stop_fetching:
                break
            await asyncio.sleep(1)
    except Exception as e:
        logger.exception(f"Error fetching messages for chat_id={chat_id}: {e}")


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
        async with session.begin():
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

                logger.info(f"Fetching messages for {chat_id}")
                min_message_id = 0
                while_True
                    load_from_date = active_configs[chat_id].load_from_date
                    messages_gen = messages_generator(
                        client, chat_id, load_from_date
                    )
                    logger.info(f"Fetching messages for {chat_id}")
                    async for batch in take_batch(messages_gen):
                        for msg in batch:
                            await message_repo.save_message(msg)
                        logger.info(f"Saved messages batch: {len(batch)}")
                        await session.flush()
                        await session.commit()
