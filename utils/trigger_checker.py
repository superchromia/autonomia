"""
Trigger checking system for bot responses.

This module provides an easily expandable system for checking if the bot
should respond to a message based on configured triggers.
"""

import logging
from typing import Any, Dict, Optional

from telethon.tl.custom.message import Message as TelegramMessage

logger = logging.getLogger("trigger_checker")

# Default trigger configuration
DEFAULT_TRIGGERS = {
    "on_every_message": False,
    "on_mention": True,
    "on_reply_to_bot": True,
}


class TriggerChecker:
    """Checks if bot should respond based on configured triggers."""

    def __init__(self, bot_id: int, bot_username: Optional[str] = None):
        self.bot_id = bot_id
        self.bot_username = bot_username

    def should_respond(
        self,
        message: TelegramMessage,
        triggers_config: Optional[Dict[str, Any]] = None,
        is_reply_to_bot: bool = False,
    ) -> bool:
        triggers = triggers_config or DEFAULT_TRIGGERS.copy()

        # Check each trigger type
        if triggers.get("on_every_message", False):
            logger.debug("Trigger: on_every_message is enabled")
            return True

        if triggers.get("on_mention", True) and self._is_bot_mentioned(message):
            logger.debug("Trigger: on_mention matched")
            return True

        if triggers.get("on_reply_to_bot", True) and is_reply_to_bot:
            logger.debug("Trigger: on_reply_to_bot matched")
            return True

        # Add more trigger checks here as needed
        # Example:
        # if triggers.get("on_keyword", False) and self._contains_keyword(
        #     message, triggers.get("keywords", [])
        # ):
        #     return True

        logger.debug("No triggers matched")
        return False

    def _is_bot_mentioned(self, message: TelegramMessage) -> bool:
        """Check if bot is mentioned using message entities."""
        # Check message entities for user mentions
        if message.entities:
            for entity in message.entities:
                # Check if entity has user_id and matches bot_id
                if hasattr(entity, "user_id") and entity.user_id == self.bot_id:
                    return True

        return False


def check_triggers(
    message: TelegramMessage,
    bot_id: int,
    triggers_config: Optional[Dict[str, Any]] = None,
    bot_username: Optional[str] = None,
    is_reply_to_bot: bool = False,
) -> bool:
    """
    Convenience function to check if bot should respond.

    Args:
        message: The Telegram message to check
        bot_id: The bot's Telegram user ID
        triggers_config: Trigger configuration dict from ChatConfig
        bot_username: The bot's Telegram username (without @)
        is_reply_to_bot: Whether the message is a reply to bot's message

    Returns:
        True if bot should respond, False otherwise
    """
    checker = TriggerChecker(bot_id, bot_username)
    return checker.should_respond(message, triggers_config, is_reply_to_bot)
