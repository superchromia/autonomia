import asyncio
import logging

from telethon import events
from telethon.tl.custom.message import Message

from dependency import dependency
from processing.enrich_message import process_message
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
        event_repo = EventRepository(session)
        try:
            logger.debug(f"Received event: {event}")
            await event_repo.save_event(event)
        except Exception as e:
            logger.exception(f"Failed to save event: {e}")


@tg.on(events.NewMessage)
async def new_message_handler(event: events.NewMessage.Event):
    logger.debug(f"Received NewMessage: {event}")
    async for session in dependency.get_session():
        message_repo = MessageRepository(session)
        user_repo = UserRepository(session)
        chat_repo = ChatRepository(session)
        try:
            message: Message = event.message
            chat = await message.get_chat()
            user = await message.get_sender()

            await message_repo.save_message(message)
            await chat_repo.save_chat(chat)
            await user_repo.save_user(user)
            await tg.send_read_acknowledge(chat, message)

            await process_message(session, chat_id=chat.id, message_id=message.id)

        except Exception as e:
            logger.exception(f"Failed to save message: {e}")


@tg.on(events.MessageEdited)
async def message_edited_handler(event: events.MessageEdited.Event):
    logger.debug(f"Received MessageEdited: {event}")
    async for session in dependency.get_session():
        message_repo = MessageRepository(session)
        try:
            logger.info(f"Received : {event}")
            await message_repo.save_message(event.message)
        except Exception as e:
            logger.exception(f"Failed to update message: {e}")


@tg.on(events.MessageDeleted)
async def message_deleted_handler(event: events.MessageDeleted.Event):
    logger.debug(f"Received MessageDeleted: {event}")
    async for session in dependency.get_session():
        try:
            message_repo = MessageRepository(session)
            await message_repo.delete_messages(chat_id=event.chat_id, deleted_ids=event.deleted_ids)
        except Exception as e:
            logger.exception(f"Failed to delete message: {e}")
