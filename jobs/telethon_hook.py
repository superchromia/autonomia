import asyncio
import logging

from sqlalchemy.future import select
from telethon import events
from telethon.tl.custom.message import Message

from dependency import dependency
from models.chat import Chat
from models.chat_config import ChatConfig
from models.message import Message as DBMessage
from models.user import User as DBUser
from processing.enrich_message import process_message
from utils.telegram_serializer import safe_telegram_to_dict

logger = logging.getLogger("telethon_hook")

tg = dependency.telegram_client


@tg.on(events.NewMessage)
async def new_message_handler(event: events.NewMessage.Event):
    logger.debug(f"Received NewMessage: {event}")
    async for session in dependency.get_session():
        try:
            message: Message = event.message
            chat = await message.get_chat()
            user = await message.get_sender()

            # Check if message already exists
            result = await session.execute(select(DBMessage).where(DBMessage.message_id == message.id, DBMessage.chat_id == chat.id))
            existing_message = result.scalar_one_or_none()

            if existing_message:
                # Update existing message
                existing_message.sender_id = user.id if user else None
                existing_message.date = message.date
                existing_message.message_type = message.media.__class__.__name__ if message.media else "text"
                existing_message.raw_data = safe_telegram_to_dict(message)
            else:
                # Save new message
                db_message = DBMessage(
                    message_id=message.id,
                    chat_id=chat.id,
                    sender_id=user.id if user else None,
                    date=message.date,
                    message_type=message.media.__class__.__name__ if message.media else "text",
                    is_read=False,
                    is_deleted=False,
                    raw_data=safe_telegram_to_dict(message),
                )
                session.add(db_message)

            # Check if chat already exists
            result = await session.execute(select(Chat).where(Chat.id == chat.id))
            existing_chat = result.scalar_one_or_none()

            if existing_chat:
                # Update existing chat
                existing_chat.chat_type = chat.__class__.__name__
                existing_chat.title = getattr(chat, "title", None)
                existing_chat.username = getattr(chat, "username", None)
                existing_chat.is_verified = getattr(chat, "verified", False)
                existing_chat.is_scam = getattr(chat, "scam", False)
                existing_chat.is_fake = getattr(chat, "fake", False)
                existing_chat.member_count = getattr(chat, "participants_count", 0)
                existing_chat.raw_data = safe_telegram_to_dict(chat)
            else:
                # Create new chat
                db_chat = Chat(
                    id=chat.id,
                    chat_type=chat.__class__.__name__,
                    title=getattr(chat, "title", None),
                    username=getattr(chat, "username", None),
                    is_verified=getattr(chat, "verified", False),
                    is_scam=getattr(chat, "scam", False),
                    is_fake=getattr(chat, "fake", False),
                    member_count=getattr(chat, "participants_count", 0),
                    raw_data=safe_telegram_to_dict(chat),
                )
                session.add(db_chat)

            # Save user
            if user:
                # Check if user already exists
                result = await session.execute(select(DBUser).where(DBUser.id == user.id))
                existing_user = result.scalar_one_or_none()

                if existing_user:
                    # Update existing user
                    existing_user.first_name = getattr(user, "first_name", None)
                    existing_user.last_name = getattr(user, "last_name", None)
                    existing_user.username = getattr(user, "username", None)
                    existing_user.is_bot = getattr(user, "bot", False)
                    existing_user.is_verified = getattr(user, "verified", False)
                    existing_user.is_scam = getattr(user, "scam", False)
                    existing_user.is_fake = getattr(user, "fake", False)
                    existing_user.is_premium = getattr(user, "premium", False)
                    existing_user.raw_data = safe_telegram_to_dict(user)
                else:
                    # Create new user
                    db_user = DBUser(
                        id=user.id,
                        first_name=getattr(user, "first_name", None),
                        last_name=getattr(user, "last_name", None),
                        username=getattr(user, "username", None),
                        is_bot=getattr(user, "bot", False),
                        is_verified=getattr(user, "verified", False),
                        is_scam=getattr(user, "scam", False),
                        is_fake=getattr(user, "fake", False),
                        is_premium=getattr(user, "premium", False),
                        raw_data=safe_telegram_to_dict(user),
                    )
                    session.add(db_user)

            await session.commit()
            await tg.send_read_acknowledge(chat, message)

            # Check if enrichment is enabled for this chat
            result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat.id))
            chat_config = result.scalar_one_or_none()
            if chat_config and chat_config.enrich_messages:
                await process_message(session, chat_id=chat.id, message_id=message.id)
            else:
                logger.debug(f"Message enrichment disabled for chat {chat.id}")

        except Exception as e:
            logger.exception(f"Failed to save message: {e}")


@tg.on(events.MessageEdited)
async def message_edited_handler(event: events.MessageEdited.Event):
    logger.debug(f"Received MessageEdited: {event}")
    async for session in dependency.get_session():
        try:
            logger.info(f"Received : {event}")
            # Update message in database
            result = await session.execute(select(DBMessage).where(DBMessage.chat_id == event.chat_id, DBMessage.message_id == event.message.id))
            db_message = result.scalar_one_or_none()
            if db_message:
                db_message.raw_data = safe_telegram_to_dict(event.message)
                await session.commit()
        except Exception as e:
            logger.exception(f"Failed to update message: {e}")


@tg.on(events.MessageDeleted)
async def message_deleted_handler(event: events.MessageDeleted.Event):
    logger.debug(f"Received MessageDeleted: {event}")
    async for session in dependency.get_session():
        try:
            # Mark messages as deleted
            await session.execute(
                DBMessage.__table__.update().where(DBMessage.chat_id == event.chat_id, DBMessage.message_id.in_(event.deleted_ids)).values(is_deleted=True)
            )
            await session.commit()
        except Exception as e:
            logger.exception(f"Failed to delete message: {e}")
