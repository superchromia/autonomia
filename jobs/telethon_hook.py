import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from telethon import events
from telethon.tl.custom.message import Message
from telethon.tl.types import Chat, User

from dependency import dependency
from models.chat import Chat as DBChat
from models.chat_config import ChatConfig
from models.message import Message as DBMessage
from models.user import User as DBUser
from processing.enrich_message import generate_bot_response
from utils.telegram_serializer import safe_telegram_to_dict
from utils.trigger_checker import check_triggers

logger = logging.getLogger("telethon_hook")

tg = dependency.telegram_client

# TODO: Get message's max length from telegram, not magic numbers
max_message_length = 1265

async def create_chat(session: AsyncSession, chat: Chat) -> None:
    result = await session.execute(select(DBChat).where(DBChat.id == chat.id))
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
        db_chat = DBChat(
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
        logger.info(f"Saved chat {chat.id} to database")


async def create_user(session: AsyncSession, user: User) -> None:
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


async def create_message(session: AsyncSession, message: Message, chat: Chat, user: User) -> None:
    result = await session.execute(
        select(DBMessage).where(
            DBMessage.message_id == message.id,
            DBMessage.chat_id == chat.id,
        )
    )
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
            message_type=(message.media.__class__.__name__ if message.media else "text"),
            is_read=False,
            is_deleted=False,
            raw_data=safe_telegram_to_dict(message),
        )
        session.add(db_message)

async def check_should_respond(session: AsyncSession, message: Message, chat: Chat) -> bool:
    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat.id))
    chat_config = result.scalar_one_or_none()
    if chat_config and chat_config.response_triggers:
        if chat_config.response_triggers.get("on_every_message", False):
            return True
        if chat_config.response_triggers.get("on_mention", False) and getattr(message, "mentioned", False):
            return True
    return False


async def respond_to_message(session: AsyncSession, message: Message, chat: Chat, user: User) -> None:
    should_respond = await check_should_respond(session, message, chat)
    if not should_respond:
        return
    async with tg.action(chat, "typing"):
        bot_response = await generate_bot_response(session, chat_id=chat.id, message_id=message.id)
        if bot_response:
            try:
                length: int = len(bot_response)
                message_part: int = 0

                while length > message_part * max_message_length:
                    await tg.send_message(chat, bot_response[:max_message_length * message_part], reply_to=message.id)
                    message_part += 1
                
                logger.info(f"Sent bot response to message {message.id} " f"in chat {chat.id}")
            except Exception as e:
                logger.exception(f"Failed to send bot response: {e}")


@tg.on(events.NewMessage(incoming=True))
async def new_message_handler(event: events.NewMessage.Event):
    logger.info(f"Received NewMessage (outgoing={event.out}): {event}")
    message: Message = event.message
    chat = await message.get_chat()
    user = await message.get_sender()

    async for session in dependency.get_session():
        try:
            await create_chat(session, chat)
            if user:
                await create_user(session, user)
            await create_message(session, message, chat, user)
            await session.commit()
            await tg.send_read_acknowledge(chat, message)
            await respond_to_message(session, message, chat, user)
        except Exception as e:
            logger.exception(f"Failed to save message: {e}")


@tg.on(events.NewMessage(outgoing=True))
async def new_message_handler(event: events.NewMessage.Event):
    logger.info(f"Received NewMessage (outgoing={event.out}): {event}")
    message: Message = event.message
    chat = await message.get_chat()
    user = await message.get_sender()
    async for session in dependency.get_session():
        try:
            await create_chat(session, chat)
            if user:
                await create_user(session, user)
            await create_message(session, message, chat, user)
        except Exception as e:
            logger.exception(f"Failed to save message: {e}")


@tg.on(events.MessageEdited)
async def message_edited_handler(event: events.MessageEdited.Event):
    logger.debug(f"Received MessageEdited: {event}")
    async for session in dependency.get_session():
        try:
            logger.info(f"Received : {event}")
            # Update message in database
            result = await session.execute(
                select(DBMessage).where(
                    DBMessage.chat_id == event.chat_id,
                    DBMessage.message_id == event.message.id,
                )
            )
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
                DBMessage.__table__.update()
                .where(
                    DBMessage.chat_id == event.chat_id,
                    DBMessage.message_id.in_(event.deleted_ids),
                )
                .values(is_deleted=True)
            )
            await session.commit()
        except Exception as e:
            logger.exception(f"Failed to delete message: {e}")
