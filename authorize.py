#!/usr/bin/env python3
"""
Script for creating a new StringSession through authorization
Used for deployment on cloud platforms
"""

import asyncio
import logging
import os

from telethon import TelegramClient
from telethon.sessions import StringSession

# Logging configuration
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def create_string_session():
    """Creates a new StringSession through authorization"""

    # Get API keys from environment variables
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    phone = os.environ.get("PHONE_NUMBER")

    if not api_id or not api_hash:
        logger.error("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
        return

    try:
        # Create client with StringSession
        client = TelegramClient(StringSession(), int(api_id), api_hash)

        logger.info("Connecting to Telegram...")
        await client.connect()

        if not await client.is_user_authorized():
            logger.info("Authorization required. Enter phone number:")
            await client.send_code_request(phone)
            logger.info("Verification code sent to your phone")

            code = input("Enter verification code: ")
            try:
                await client.sign_in(phone, code)
            except Exception:
                logger.info("Two-factor authentication password required")
                password = input("Enter password: ")
                await client.sign_in(password=password)
        else:
            logger.info("User already authorized")

        # Get StringSession
        string_session = client.session.save()

        logger.info("=" * 60)
        logger.info("STRING SESSION (copy this string to environment variable):")
        logger.info("=" * 60)
        logger.info(string_session)
        logger.info("=" * 60)
        logger.info(
            "Now add this string to the TELETHON_SESSION_STRING environment variable in Render"
        )

        await client.disconnect()

    except Exception as e:
        logger.error(f"Error creating session: {e}")


if __name__ == "__main__":
    asyncio.run(create_string_session())
