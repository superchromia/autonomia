import logging

from telethon import events
from telethon.tl.custom.message import Message

from dependency import dependency
from repositories.chat_repository import ChatRepository
from repositories.event_repository import EventRepository
from repositories.message_repository import MessageRepository
from repositories.user_repository import UserRepository

logger = logging.getLogger("telethon_hook")

tg = dependency.telegram_client


@tg.on(events.NewMessage)
@tg.on(events.MessageEdited)
@tg.on(events.MessageDeleted)
@tg.on(events.ChatAction)
async def events_handler(event):
    async for session in dependency.get_session():
        async with session.begin():
            event_repo = EventRepository(session)
            try:
                logger.info(f"Received event: {event}")
                await event_repo.save_event(event)
                await session.flush()
            except Exception as e:
                logger.exception(f"Failed to save event: {e}")


@tg.on(events.NewMessage)
async def new_message_handler(event: events.NewMessage.Event):
    logger.info(f"Received NewMessage: {event}")
    async for session in dependency.get_session():
        async with session.begin():
            message_repo = MessageRepository(session)
            user_repo = UserRepository(session)
            chat_repo = ChatRepository(session)
            try:
                logger.info(f"Received message: {event}")

                message: Message = event.message
                chat = await message.get_chat()
                user = await message.get_sender()

                await message_repo.create_message(message)
                await chat_repo.save_chat(chat)
                await user_repo.save_user(user)
                await tg.send_read_acknowledge(chat, message)

                await session.flush()
            except Exception as e:
                logger.exception(f"Failed to save message: {e}")


@tg.on(events.MessageEdited)
async def message_edited_handler(event: events.MessageEdited.Event):
    logger.info(f"Received MessageEdited: {event}")
    async for session in dependency.get_session():
        async with session.begin():
            message_repo = MessageRepository(session)
            try:
                logger.info(f"Received : {event}")
                await message_repo.update_message(event.message)
                await session.flush()
            except Exception as e:
                logger.exception(f"Failed to update message: {e}")


@tg.on(events.MessageDeleted)
async def message_deleted_handler(event: events.MessageDeleted.Event):
    logger.info(f"Received MessageDeleted: {event}")
    async for session in dependency.get_session():
        async with session.begin():
            try:
                message_repo = MessageRepository(session)
                await message_repo.delete_messages(
                    chat_id=event.chat_id, deleted_ids=event.deleted_ids
                )
                await session.flush()
            except Exception as e:
                logger.exception(f"Failed to delete message: {e}")
