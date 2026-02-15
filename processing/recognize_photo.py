"""Photo recognition using vision models."""

import base64
import logging
import os
import time

from openai import AsyncOpenAI
from sqlalchemy.future import select
from telethon.tl.custom.message import Message as TelegramMessage
from telethon.tl.types import MessageMediaPhoto

from models.chat_config import ChatConfig
from models.media import Media

logger = logging.getLogger("recognize_photo")

ai_client = AsyncOpenAI(
    base_url=os.environ.get(
        "NEBIUS_BASE_URL",
        "https://api.tokenfactory.nebius.com/v1/",
    ),
    api_key=os.environ.get("NEBIUS_API_KEY")
    or os.environ.get("NEBIUS_STUDIO_API_KEY"),
)


async def recognize_photo(
    session,
    telegram_client,
    message: TelegramMessage,
    chat_id: int,
    message_id: int,
) -> str | None:
    """
    Recognize and describe a photo from a Telegram message.

    Args:
        session: Database session
        telegram_client: Telegram client for downloading photos
        message: Telegram message object
        chat_id: Chat ID
        message_id: Message ID

    Returns:
        Text description of the photo, or None if recognition failed
    """
    # Check if message has photo media
    if not message.media or not isinstance(message.media, MessageMediaPhoto):
        return None

    # Get chat config
    result = await session.execute(select(ChatConfig).where(ChatConfig.chat_id == chat_id))
    chat_config = result.scalar_one_or_none()

    if not chat_config:
        raise ValueError(f"ChatConfig not found for chat_id={chat_id}")

    if not chat_config.recognize_photo:
        logger.debug(f"Photo recognition disabled for chat_id={chat_id}")
        return None

    if not chat_config.image_model:
        raise ValueError(f"image_model not configured for chat_id={chat_id}")

    try:
        # Download photo from Telegram
        photo_bytes = await telegram_client.download_media(message.media, file=bytes)
        if not photo_bytes:
            logger.warning(f"Failed to download photo for message {message_id}")
            return None

        # Convert to base64
        photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")

        # Get MIME type (default to JPEG)
        mime_type = "image/jpeg"
        if hasattr(message.media, "mime_type") and message.media.mime_type:
            mime_type = message.media.mime_type

        # Get message caption if available
        caption = message.message or ""
        if caption:
            prompt_text = f"Опиши это изображение подробно на русском языке. " f"Что на нём изображено?\n\n" f"Подпись к изображению: {caption}"
        else:
            prompt_text = "Опиши это изображение подробно на " "русском языке. Что на нём изображено?"

        # Call vision API
        response = await ai_client.chat.completions.create(
            model=chat_config.image_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt_text,
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (f"data:{mime_type};base64,{photo_base64}"),
                            },
                        },
                    ],
                },
            ],
        )

        description = response.choices[0].message.content.strip()
        logger.info(f"Recognized photo for message {message_id} in chat {chat_id}")

        # Save or update media record
        photo_id = message.media.photo.id if hasattr(message.media.photo, "id") else message_id
        file_reference = f"{chat_id}_{message_id}_{photo_id}"

        result = await session.execute(select(Media).where(Media.file_reference == file_reference))
        existing_media = result.scalar_one_or_none()

        if existing_media:
            existing_media.text_description = description
            existing_media.updated_at = int(time.time() * 1000)
            logger.info(f"Updated media description for {file_reference}")
        else:
            current_timestamp = int(time.time() * 1000)
            db_media = Media(
                file_reference=file_reference,
                chat_id=chat_id,
                message_id=message_id,
                media_type="photo",
                text_description=description,
                created_at=current_timestamp,
                updated_at=current_timestamp,
            )
            session.add(db_media)
            logger.info(f"Created media record for {file_reference}")

        await session.commit()
        return description

    except Exception as e:
        logger.exception(f"Failed to recognize photo for message {message_id}: {e}")
        return None
