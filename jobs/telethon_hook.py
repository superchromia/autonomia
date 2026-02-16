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
from processing.enrich_message import generate_bot_response, process_message
from utils.telegram_serializer import safe_telegram_to_dict
from utils.trigger_checker import check_triggers

logger = logging.getLogger("telethon_hook")

tg = dependency.telegram_client


def _safe_attr(obj, name, default=None):
    value = getattr(obj, name, default)
    # MagicMock creates nested mocks for missing attributes; treat them as absent.
    if value.__class__.__name__ == "MagicMock":
        return default
    return value


def _safe_bool_attr(obj, name, default=False):
    value = _safe_attr(obj, name, default)
    return value if isinstance(value, bool) else default


def _safe_int_attr(obj, name, default=0):
    value = _safe_attr(obj, name, default)
    return value if isinstance(value, int) else default


async def create_chat(session: AsyncSession, chat: Chat) -> None:
    result = await session.execute(select(DBChat).where(DBChat.id == chat.id))
    existing_chat = result.scalar_one_or_none()

    if existing_chat:
        # Update existing chat
        existing_chat.chat_type = chat.__class__.__name__
        existing_chat.title = _safe_attr(chat, "title", None)
        existing_chat.username = _safe_attr(chat, "username", None)
        existing_chat.is_verified = _safe_bool_attr(chat, "verified", False)
        existing_chat.is_scam = _safe_bool_attr(chat, "scam", False)
        existing_chat.is_fake = _safe_bool_attr(chat, "fake", False)
        existing_chat.member_count = _safe_int_attr(chat, "participants_count", 0)
        existing_chat.raw_data = safe_telegram_to_dict(chat)
    else:
        # Create new chat
        db_chat = DBChat(
            id=chat.id,
            chat_type=chat.__class__.__name__,
            title=_safe_attr(chat, "title", None),
            username=_safe_attr(chat, "username", None),
            is_verified=_safe_bool_attr(chat, "verified", False),
            is_scam=_safe_bool_attr(chat, "scam", False),
            is_fake=_safe_bool_attr(chat, "fake", False),
            member_count=_safe_int_attr(chat, "participants_count", 0),
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


async def create_message(session: AsyncSession, message: Message, chat: Chat, user: User | None = None) -> None:
    result = await session.execute(
        select(DBMessage).where(
            DBMessage.message_id == message.id,
            DBMessage.chat_id == chat.id,
        )
    )
    existing_message = result.scalar_one_or_none()

    if existing_message:
        # Update existing message
        existing_message.sender_id = user.id if user else message.sender_id
        existing_message.date = message.date
        existing_message.message_type = message.media.__class__.__name__ if message.media else "text"
        existing_message.raw_data = safe_telegram_to_dict(message)
    else:
        # Save new message
        db_message = DBMessage(
            message_id=message.id,
            chat_id=chat.id,
            sender_id=user.id if user else message.sender_id,
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
                response_message = await tg.send_message(chat, bot_response, reply_to=message.id)
                logger.info(f"Sent bot response to message {message.id} " f"in chat {chat.id}")
                return response_message
            except Exception as e:
                logger.exception(f"Failed to send bot response: {e}")


async def enrich_message_if_enabled(session: AsyncSession, message: Message, chat: Chat) -> None:
    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat.id))
    chat_config = result.scalar_one_or_none()
    if not chat_config or not chat_config.enrich_messages:
        return

    try:
        await process_message(session, chat_id=chat.id, message_id=message.id)
    except Exception as e:
        # Enrichment is optional and must not break message persistence flow.
        logger.warning(
            "Failed to enrich message %s in chat %s: %s",
            message.id,
            chat.id,
            e,
        )


@tg.on(events.NewMessage)
async def new_message_handler(event: events.NewMessage):
    logger.info(f"Received NewMessage: {event}")
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
            await enrich_message_if_enabled(session, message, chat)
        except Exception as e:
            logger.exception(f"Failed to save message: {e}")
    return event


@tg.on(events.NewMessage(incoming=True))
async def new_outgoing_message_handler(event: events.NewMessage.Event):
    message: Message = event.message
    chat = await message.get_chat()
    user = await message.get_sender()
    async for session in dependency.get_session():
        try:
            await tg.send_read_acknowledge(chat, message)
            message = await respond_to_message(session, message, chat, user)
            if message:
                await create_message(session, message, chat, user=await get_me())
                await session.commit()
        except Exception as e:
            logger.exception(f"Failed to save message: {e}")
    return event


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
    return event


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
    return event


async def get_me() -> User:
    me = await tg.get_me()
    return me
