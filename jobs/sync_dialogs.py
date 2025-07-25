import logging

from telethon import types

from dependency import dependency
from repositories.chat_repository import ChatRepository
from repositories.user_repository import UserRepository

logger = logging.getLogger("sync_dialogs")


async def sync_dialogs_job():
    """
    Job for iterating through all dialogs and saving chats and users
    """
    # Check Telegram client availability
    if not dependency.telegram_client:
        logger.warning(
            "Telegram client not available - sync dialogs job skipped"
        )
        return

    client = dependency.telegram_client
    logger.info("Sync dialogs job started")

    async for session in dependency.get_session():
        # Get repositories
        chat_repo = ChatRepository(session)
        user_repo = UserRepository(session)

        try:
            # Iterate through all dialogs
            async for dialog in client.iter_dialogs():
                dialog: types.Dialog
                entity = dialog.entity

                logger.info(
                    f"Processing dialog: {dialog.name} (ID: {entity.id})"
                )

                await chat_repo.save_chat(entity)
                logger.info(f"Saved chat: {entity}")

                if isinstance(entity, types.User):
                    await user_repo.save_user(entity)
                    logger.info(f"Saved user: {entity}")

                logger.info(f"Listing participants: {entity}")
                try:
                    async for participant in client.iter_participants(entity):
                        await user_repo.save_user(participant)
                        logger.info(f"Saved participant: {participant}")
                except Exception as e:
                    logger.error(f"Error listing participants: {e}")

            logger.info("Sync dialogs job completed successfully")

        except Exception as e:
            logger.exception(f"Error in sync dialogs job: {e}")
            raise
