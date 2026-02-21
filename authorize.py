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

# Setup logging
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


async def create_string_session():
    """Creates a new StringSession through authorization"""
    # Get API keys from environment variables
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")

    async with TelegramClient(
        session=StringSession(),
        api_id=api_id,
        api_hash=api_hash,
    ) as client:
        print("Session string: ", client.session.save())


if __name__ == "__main__":
    asyncio.run(create_string_session())
