import logging
from collections.abc import AsyncGenerator
from typing import TypeVar

from sqlalchemy.future import select
from telethon import TelegramClient, types

from dependency import dependency
from models.message import Message
from utils.telegram_serializer import safe_telegram_to_dict

logger = logging.getLogger("fetch_messages")

T = TypeVar("T")


async def messages_generator(client: TelegramClient, chat_id: int, offset_id: int):
    try:
        logger.info(f"Fetching messages for chat_id={chat_id}, offset_id={offset_id}")
        async for msg in client.iter_messages(entity=chat_id, offset_id=offset_id):
            yield msg

    except Exception as e:
        logger.exception(f"Error fetching messages for chat_id={chat_id}: {e}")
        raise


async def take_batch(generator: AsyncGenerator[T, None], batch_size: int = 1000) -> AsyncGenerator[list[T], None]:
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
        async for dialog in client.iter_dialogs():
            dialog: types.Dialog
            chat_id = dialog.entity.id

            # Get first message ID for this chat
            result = await session.execute(select(Message.message_id).where(Message.chat_id == chat_id).order_by(Message.message_id.desc()).limit(1))
            first_msg = result.scalar_one_or_none()
            offset_id = first_msg if first_msg else 0
            messages_gen = messages_generator(client, chat_id, offset_id)

            async for batch in take_batch(messages_gen):
                # Save messages batch with upsert logic
                for msg in batch:
                    # Check if message already exists
                    result = await session.execute(select(Message).where(Message.message_id == msg.id, Message.chat_id == chat_id))
                    existing_message = result.scalar_one_or_none()

                    if existing_message:
                        # Update existing message
                        existing_message.sender_id = msg.sender_id if msg.sender_id else None
                        existing_message.date = msg.date
                        existing_message.message_type = msg.media.__class__.__name__ if msg.media else "text"
                        existing_message.raw_data = safe_telegram_to_dict(msg)
                    else:
                        # Create new message
                        db_message = Message(
                            message_id=msg.id,
                            chat_id=chat_id,
                            sender_id=msg.sender_id if msg.sender_id else None,
                            date=msg.date,
                            message_type=(msg.media.__class__.__name__ if msg.media else "text"),
                            is_read=False,
                            is_deleted=False,
                            raw_data=safe_telegram_to_dict(msg),
                        )
                        session.add(db_message)

                await session.commit()
                logger.info(f"Saved messages batch: {len(batch)}")
