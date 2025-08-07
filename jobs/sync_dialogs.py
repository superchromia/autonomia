import logging

from telethon import types

from dependency import dependency
from models.chat import Chat
from models.user import User
from utils.telegram_serializer import safe_telegram_to_dict

logger = logging.getLogger("sync_dialogs")


async def sync_dialogs_job():
    """
    Job for iterating through all dialogs and saving chats and users
    """
    # Check Telegram client availability
    if not dependency.telegram_client:
        logger.warning("Telegram client not available - sync dialogs job skipped")
        return

    client = dependency.telegram_client
    logger.info("Sync dialogs job started")

    async for session in dependency.get_session():
        try:
            # Iterate through all dialogs
            async for dialog in client.iter_dialogs():
                dialog: types.Dialog
                entity = dialog.entity

                logger.info(f"Processing dialog: {dialog.name} (ID: {entity.id})")

                # Save chat
                db_chat = Chat(
                    id=entity.id,
                    chat_type=entity.__class__.__name__,
                    title=getattr(entity, "title", None),
                    username=getattr(entity, "username", None),
                    is_verified=getattr(entity, "verified", False),
                    is_scam=getattr(entity, "scam", False),
                    is_fake=getattr(entity, "fake", False),
                    member_count=getattr(entity, "participants_count", 0),
                    raw_data=safe_telegram_to_dict(entity),
                )
                session.add(db_chat)
                logger.info(f"Saved chat: {entity}")

                if isinstance(entity, types.User):
                    # Save user
                    db_user = User(
                        id=entity.id,
                        first_name=getattr(entity, "first_name", None),
                        last_name=getattr(entity, "last_name", None),
                        username=getattr(entity, "username", None),
                        is_bot=getattr(entity, "bot", False),
                        is_verified=getattr(entity, "verified", False),
                        is_scam=getattr(entity, "scam", False),
                        is_fake=getattr(entity, "fake", False),
                        is_premium=getattr(entity, "premium", False),
                        raw_data=safe_telegram_to_dict(entity),
                    )
                    session.add(db_user)
                    logger.info(f"Saved user: {entity}")

                logger.info(f"Listing participants: {entity}")
                try:
                    async for participant in client.iter_participants(entity):
                        # Save participant
                        db_participant = User(
                            id=participant.id,
                            first_name=getattr(participant, "first_name", None),
                            last_name=getattr(participant, "last_name", None),
                            username=getattr(participant, "username", None),
                            is_bot=getattr(participant, "bot", False),
                            is_verified=getattr(participant, "verified", False),
                            is_scam=getattr(participant, "scam", False),
                            is_fake=getattr(participant, "fake", False),
                            is_premium=getattr(participant, "premium", False),
                            raw_data=safe_telegram_to_dict(participant),
                        )
                        session.add(db_participant)
                        logger.info(f"Saved participant: {participant}")
                except Exception as e:
                    logger.error(f"Error listing participants: {e}")

            await session.commit()
            logger.info("Sync dialogs job completed successfully")

        except Exception as e:
            logger.exception(f"Error in sync dialogs job: {e}")
            raise
